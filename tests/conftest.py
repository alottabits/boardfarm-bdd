"""pytest-bdd conftest.py - Auto-discover and register step definitions for pytest-bdd."""

import ast
import importlib
from pathlib import Path

import pytest
from boardfarm3.templates.acs import ACS as AcsTemplate
from boardfarm3.templates.cpe.cpe import CPE as CpeTemplate
from boardfarm3.templates.wan import WAN as WanTemplate
from pytest_bdd import given, parsers, then, when
from pytest_boardfarm3.boardfarm_fixtures import devices

# Auto-discover and import all step definition modules
# This ensures pytest-bdd can find them even if re-registration has issues
step_defs_dir = Path(__file__).parent / "step_defs"
if step_defs_dir.exists():
    for step_file in step_defs_dir.glob("*.py"):
        # Skip __init__.py and helpers.py (not step definitions)
        if step_file.stem not in ("__init__", "helpers"):
            try:
                module_name = f"tests.step_defs.{step_file.stem}"
                importlib.import_module(module_name)
            except ImportError as e:
                # If imports fail during development, that's okay - re-registration will handle it
                print(f"Warning: Could not import {module_name}: {e}")
                pass



def _extract_step_decorators_from_source(module_path: Path):
    """Extract step decorator information from Python source code using AST.
    
    Returns a list of dictionaries with step information:
    - type: 'given', 'when', or 'then'
    - name: the step name string
    - function_name: the name of the function being decorated
    - uses_parser: True if the step uses parsers.parse(), False otherwise
    """
    import re
    steps = []
    
    try:
        with open(module_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(module_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Look for @given, @when, @then decorators
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Name):
                            decorator_name = decorator.func.id
                            if decorator_name in ("given", "when", "then"):
                                # Extract step name (first argument)
                                # Python automatically concatenates adjacent string literals,
                                # so we can check for ast.Constant directly
                                if decorator.args and isinstance(
                                    decorator.args[0], ast.Constant
                                ):
                                    step_name = decorator.args[0].value
                                    # Check if step contains parameter placeholders like {param}
                                    # Parameterized steps should use parsers.parse() for proper matching
                                    has_parameters = bool(re.search(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', step_name))
                                    steps.append({
                                        "type": decorator_name,
                                        "name": step_name,
                                        "function_name": node.name,
                                        "uses_parser": has_parameters  # Use parsers.parse() for parameterized steps
                                    })
                                # Also handle parsers.parse() patterns
                                elif decorator.args and isinstance(
                                    decorator.args[0], ast.Call
                                ):
                                    # Handle cases like @given(parsers.parse("..."))
                                    call_func = decorator.args[0].func
                                    if (
                                        isinstance(call_func, ast.Attribute)
                                        and call_func.attr == "parse"
                                    ):
                                        if decorator.args[0].args and isinstance(
                                            decorator.args[0].args[0], ast.Constant
                                        ):
                                            step_name = decorator.args[0].args[0].value
                                            steps.append({
                                                "type": decorator_name,
                                                "name": step_name,
                                                "function_name": node.name,
                                                "uses_parser": True  # Mark as using parsers.parse()
                                            })
    except Exception as e:
        print(f"  ✗ Error parsing {module_path}: {e}")
    
    return steps


def _discover_and_register_step_definitions():
    """Auto-discover all step definitions and re-register them.
    
    This function:
    1. Finds all Python modules in pytest/step_defs/
    2. Parses them with AST to find step decorators
    3. Imports the modules to get function objects
    4. Re-registers all step definitions so pytest-bdd can discover them
    """
    step_defs_dir = Path(__file__).parent / "step_defs"
    
    if not step_defs_dir.exists():
        print(f"Warning: Step definitions directory not found: {step_defs_dir}")
        return
    
    # Get all Python files (excluding __init__.py and helpers.py)
    step_files = [
        f for f in step_defs_dir.glob("*.py")
        if f.stem not in ("__init__", "helpers")
    ]
    
    if not step_files:
        print("conftest.py: No step definition files found")
        return
    
    print(f"conftest.py: Discovering step definitions from {len(step_files)} modules...")
    
    registered_count = 0
    decorators = {"given": given, "when": when, "then": then}
    # Store decorated functions to keep references alive
    _registered_steps = []
    
    for step_file in sorted(step_files):
        module_name = step_file.stem
        try:
            # Import the module to get function objects
            # This import makes the step definitions available to pytest-bdd
            module_path = f"tests.step_defs.{module_name}"
            module = importlib.import_module(module_path)
            
            # Extract step decorator info from source using AST
            step_info_list = _extract_step_decorators_from_source(step_file)
            
            if not step_info_list:
                continue
            
            for step_info in step_info_list:
                step_type = step_info["type"]
                step_name = step_info["name"]
                func_name = step_info["function_name"]
                uses_parser = step_info.get("uses_parser", False)  # Default to False for backward compatibility
                
                # Get the original function from the module
                original_func = getattr(module, func_name, None)
                if original_func and callable(original_func):
                    import sys
                    import inspect
                    conftest_module = sys.modules[__name__]

                    # Get the function signature to preserve parameter names
                    sig = inspect.signature(original_func)
                    param_names = list(sig.parameters.keys())
                    
                    # Create parameter string for the wrapper function
                    # This preserves the original signature so pytest-bdd can inject fixtures
                    if param_names:
                        params_str = ", ".join(param_names)
                    else:
                        params_str = ""
                    
                    # Create a unique function name
                    wrapper_name = f"_{module_name}_{func_name}_wrapper"

                    # Create step definition code preserving the original signature
                    # Escape quotes in step_name for the code string
                    # This preserves parameter placeholders like {username}
                    escaped_step_name = step_name.replace('"', '\\"')

                    # Generator steps (yield-based teardown) need "yield from"
                    # so pytest-bdd sees the wrapper itself as a generator and
                    # can drive the setup/teardown lifecycle correctly.
                    call_expr = (
                        f"module.{func_name}({params_str})"
                        if params_str
                        else f"module.{func_name}()"
                    )
                    delegate = (
                        f"yield from {call_expr}"
                        if inspect.isgeneratorfunction(original_func)
                        else f"return {call_expr}"
                    )

                    # Build the wrapper function code with preserved signature
                    # Use parsers.parse() if the original step used it
                    if uses_parser:
                        step_code = f'''
@decorators["{step_type}"](parsers.parse("{escaped_step_name}"))
def {wrapper_name}({params_str}):
    """Re-registered step definition wrapper."""
    {delegate}
'''
                    else:
                        step_code = f'''
@decorators["{step_type}"]("{escaped_step_name}")
def {wrapper_name}({params_str}):
    """Re-registered step definition wrapper."""
    {delegate}
'''
                    
                    # Execute in module namespace with necessary variables
                    exec_globals = {
                        "decorators": decorators,
                        "module": module,
                        "parsers": parsers,
                        "__name__": __name__,
                    }
                    exec(step_code, exec_globals, conftest_module.__dict__)  # noqa: S102
                    
                    # Get the decorated function
                    decorated_func = getattr(conftest_module, wrapper_name)
                    
                    # Ensure __module__ is set correctly so pytest-bdd can discover it
                    decorated_func.__module__ = __name__
                    
                    # Also set __qualname__ for better introspection
                    decorated_func.__qualname__ = f"{__name__}.{wrapper_name}"
                    
                    _registered_steps.append(decorated_func)
                    
                    registered_count += 1
                    parser_note = " (with parsers.parse())" if uses_parser else ""
                    print(f"  ✓ Re-registered {step_type.upper()}: '{step_name}' from {module_name}{parser_note}")
                    # Debug: Print step name with repr to see exact string
                    if "username" in step_name.lower():
                        print(f"    DEBUG: Step name repr: {repr(step_name)}")
                else:
                    print(f"  ✗ Function '{func_name}' not found in {module_name}")
            
        except Exception as e:
            print(f"  ✗ Error processing {module_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"conftest.py: Successfully registered {registered_count} step definitions")


# Run auto-discovery when conftest.py is loaded
# This must happen before pytest-bdd scans for step definitions
# Note: Step definition modules are already imported at the top of this file
# The re-registration here ensures pytest-bdd can discover them
_discover_and_register_step_definitions()


# Boardfarm device fixtures - extract devices from the devices fixture
@pytest.fixture
def acs(devices) -> AcsTemplate:
    """ACS device fixture extracted from boardfarm devices."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "genieacs", None) or getattr(devices, "acs", None)


@pytest.fixture
def cpe(devices) -> CpeTemplate:
    """CPE device fixture extracted from boardfarm devices."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "board", None) or getattr(devices, "cpe", None)


@pytest.fixture
def http_server(devices) -> WanTemplate:
    """HTTP server (WAN) device fixture extracted from boardfarm devices."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "wan", None)


@pytest.fixture
def wan(devices) -> WanTemplate:
    """WAN device fixture (alias for http_server)."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "wan", None)


@pytest.fixture
def lan_phone(devices):
    """LAN phone device fixture extracted from boardfarm devices."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "lan_phone", None)


@pytest.fixture
def wan_phone(devices):
    """WAN phone device fixture extracted from boardfarm devices."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "wan_phone", None)


@pytest.fixture
def wan_phone2(devices):
    """WAN phone 2 device fixture extracted from boardfarm devices."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "wan_phone2", None)


@pytest.fixture
def sipcenter(devices):
    """SIP center (Kamailio) device fixture extracted from boardfarm devices."""
    # devices is a Namespace object, access via attributes
    return getattr(devices, "sipcenter", None)


@pytest.fixture
def sdwan(devices):
    """SD-WAN appliance (LinuxSDWANRouter) when available (e.g. --board-name sdwan)."""
    return getattr(devices, "sdwan", None)


@pytest.fixture
def boardfarm_config(request):
    """Boardfarm config object for accessing env config (presets, etc.).

    Uses the boardfarm plugin's config when available; falls back to None
    for unit tests.
    """
    plugin = request.config.pluginmanager.get_plugin("_boardfarm")
    if plugin is not None:
        return plugin.boardfarm_config
    return None


@pytest.fixture(scope="function", autouse=True)
def refresh_cpe_console_after_scenario(cpe: CpeTemplate):
    """Refresh the CPE console connection after each scenario.

    This is a cross-cutting concern: any scenario might reboot the CPE, leaving
    the console connection stale. Re-establishing the connection here keeps the
    next scenario from inheriting a dead session.

    CPE config restoration (passwords, parameters) is handled by yield-based
    teardown in the individual step definitions that change those values.
    """
    yield

    if cpe is None:
        return

    try:
        cpe.hw.disconnect_from_consoles()
    except Exception:
        pass

    try:
        device_name = getattr(cpe, "device_name", "cpe")
        cpe.hw.connect_to_consoles(device_name)
    except Exception:
        pass



