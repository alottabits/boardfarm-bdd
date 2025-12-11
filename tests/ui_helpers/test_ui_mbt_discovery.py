
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
# Import dynamically or assume path is correct now
# from ui_mbt_discovery import UIStateMachineDiscovery, UIState, ActionType
import sys
import os

# Ensure import works
sys.path.append(os.getcwd())
try:
    from ui_mbt_discovery import UIStateMachineDiscovery, UIState, ActionType
except ImportError:
    # Fallback if running from root
    from boardfarm_bdd.tests.ui_helpers.ui_mbt_discovery import UIStateMachineDiscovery, UIState, ActionType

@pytest.fixture
def discovery_tool():
    return UIStateMachineDiscovery(base_url="http://mock.com")

def test_identify_forms_standard_form(discovery_tool):
    async def run_test():
        # Mock Page
        mock_page = MagicMock() # Page has mixed methods
        
        # Mock Form Elements
        mock_form = MagicMock() # Locator object
        mock_input = MagicMock() # Locator object
        mock_button = MagicMock() # Locator object
        
        # Setup Page Locator
        # page.locator("form:visible").all()
        mock_page_locator = MagicMock()
        mock_page.locator.return_value = mock_page_locator
        mock_page_locator.all = AsyncMock(return_value=[mock_form])
        
        # Setup Form Locator (inputs and buttons)
        # form.locator(...) returns a Locator, whose .all() is async
        
        def locator_side_effect(selector):
            print(f"DEBUG: locator called with {selector}")
            loc = MagicMock()
            # Strict logic: check button first or use exact string
            if "button" in selector or "submit" in selector:
                loc.all = AsyncMock(return_value=[mock_button])
                print("DEBUG: Returning button locator")
            elif "input" in selector:
                loc.all = AsyncMock(return_value=[mock_input])
                print("DEBUG: Returning input locator")
            else:
                loc.all = AsyncMock(return_value=[])
                print("DEBUG: Returning empty locator")
            return loc
            
        mock_form.locator.side_effect = locator_side_effect
        
        # is_visible is async
        mock_button.is_visible = AsyncMock(return_value=True)
        
        # Mock _get_unique_selector and descriptors (methods on tool)
        discovery_tool._get_unique_selector = AsyncMock(return_value="form#login")
        discovery_tool._get_element_descriptor = AsyncMock(return_value={"type": "mock"})

        print("DEBUG: Calling _identify_forms")
        # Execute
        forms = await discovery_tool._identify_forms(mock_page)
        print(f"DEBUG: identify_forms returned {forms}")
        
        # Verify
        assert len(forms) == 1
        assert forms[0]["type"] == "standard_form"
        assert forms[0]["locator"] == "form#login"
        assert len(forms[0]["inputs"]) == 1
        assert len(forms[0]["buttons"]) == 1

    asyncio.run(run_test())

def test_identify_forms_no_form(discovery_tool):
    async def run_test():
        mock_page = AsyncMock()
        mock_page.locator.return_value.all.return_value = [] # No forms
        
        forms = await discovery_tool._identify_forms(mock_page)
        assert len(forms) == 0
    
    asyncio.run(run_test())

def test_execute_form_fill(discovery_tool):
    async def run_test():
        mock_page = AsyncMock()
        mock_page.url = "http://mock.com"
        
        # Mock state
        from_state = UIState(state_id="A", state_type="form")
        discovery_tool.states["A"] = from_state
        
        # Mock locator finding
        mock_input_loc = AsyncMock()
        mock_btn_loc = AsyncMock()
        
        # Configure _locate_element_from_descriptor to return mocks
        async def locate_side_effect(page, desc):
            if desc["type"] == "input": return mock_input_loc
            if desc["type"] == "button": return mock_btn_loc
            return None
            
        discovery_tool._locate_element_from_descriptor = AsyncMock(side_effect=locate_side_effect)
        
        # Mock discovery of new state
        new_state = UIState(state_id="B", state_type="dashboard")
        discovery_tool._discover_current_state = AsyncMock(return_value=new_state)
        
        form_info = {
            "inputs": [{"type": "input", "locators": {"input_type": "text", "name": "user"}}],
            "buttons": [{"type": "button"}]
        }
        
        # Execute
        result_state_id = await discovery_tool._execute_form_fill(
            mock_page, from_state, form_info, navigate_back=False
        )
        
        # Verify
        assert result_state_id == "B"
        mock_input_loc.fill.assert_called_with("test_value")
        mock_btn_loc.click.assert_called()
        assert len(discovery_tool.transitions) == 1
        assert discovery_tool.transitions[0].action_type == ActionType.FILL_FORM

    asyncio.run(run_test())

