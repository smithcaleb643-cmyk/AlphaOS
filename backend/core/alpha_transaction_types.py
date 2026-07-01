def extract_signed_tx(signed_result):
    """
    Forces all signer outputs into a clean base64 string.
    """

    if not signed_result:
        return None

    if isinstance(signed_result, str):
        return signed_result

    if isinstance(signed_result, dict):
        return (
            signed_result.get("signed_transaction")
            or signed_result.get("swap_transaction")
            or signed_result.get("raw")
        )

    return None