from pytest_bdd import when

@when("I say hello")
def say_hello():
    """A simple step that prints a message and passes."""
    print("Hello, BDD World!")
    assert True
