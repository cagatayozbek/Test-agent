from source import process_transaction

def test_bare_except_does_not_hide_valid_transaction_processing():
    """
    Tests that valid transaction processing is not hidden by a bare 'except:'.

    Bug: A bare 'except:' block catches all exceptions, including NameError,
    hiding a programming error and making it seem like a data format issue
    by returning None. The fixed version defines the helper and returns the
    amount including tax.
    """
    # This input string is syntactically valid and should not cause a
    # ValueError or IndexError. Its purpose is to reach the line that
    # calls the missing function.
    valid_transaction_str = "item123:100"

    result = process_transaction(valid_transaction_str)

    assert result == 118.0, (
        "Valid transactions should include calculated tax; "
        f"expected 118.0, got {result!r}"
    )
