from typing import Union


def generate_put_code(nitg_code: str) -> Union[None, str]:
    if not nitg_code.startswith("B"):
        return None

    # Remove B
    nitg_code = nitg_code[1:]

    # Split into 3 sections:
    if len(nitg_code) != 7:
        return None

    initial_code, char, second_code = nitg_code[0:2], nitg_code[2], nitg_code[3:]

    if not initial_code.isdigit():
        return None

    if not second_code.isdigit():
        return None

    if char.isdigit():
        return None

    return f"GMW{initial_code}{char}00{second_code}"
