```shell
Example: Running Individual Tests
# From /home/rjvisser/projects/req-tst/boardfarm-bdd
# Test that phone role retrieval works
.venv-3.12/bin/python -m pytest tests/unit/test_step_defs/test_sip_phone_steps.py::test_get_phone_by_role_caller -v
# Test phone idle state validation
.venv-3.12/bin/python -m pytest tests/unit/test_step_defs/test_sip_phone_steps.py::test_phone_is_idle_success -v
# Test phone registration
.venv-3.12/bin/python -m pytest tests/unit/test_step_defs/test_sip_phone_steps.py::test_ensure_phone_registered_success -v

# Run all verify_rtp_session tests
.venv-3.12/bin/python -m pytest tests/unit/test_step_defs/test_sip_phone_steps.py -k "verify_rtp_session" -v


# Run all tests in the sip_phone_steps module with coverage reporting. 
# This will generate a coverage report in the terminal and an HTML report in the coverage directory.
cd /home/rjvisser/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
pytest tests/unit/test_step_defs/test_sip_phone_steps.py --cov=tests.step_defs.sip_phone_steps --cov-report=term --cov-report=html -v


# Run all tests in the step_defs directory with coverage reporting.
cd /home/rjvisser/projects/req-tst/boardfarm-bdd
source .venv-3.12/bin/activate
pytest tests/unit/test_step_defs/ --cov=tests/step_defs --cov-report=term --no-cov-on-fail -q

