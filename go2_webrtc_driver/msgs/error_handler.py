from ..constants import app_error_messages
import time
import logging

def integer_to_hex_string(error_code):
    """
    Converts an integer error code to a hexadecimal string.
    
    Args:
        error_code (int): The error code as an integer.
        
    Returns:
        str: The error code as a hexadecimal string, without the '0x' prefix, in uppercase.
    """
    if not isinstance(error_code, int):
        raise ValueError("Input must be an integer.")

    # Convert the integer to a hex string and remove the '0x' prefix
    hex_string = hex(error_code)[2:].upper()

    return hex_string

def get_error_code_text(error_source, error_code):
    """
    Retrieve the error message based on the error source and error code.

    Args:
        error_code_dict (dict): Dictionary mapping error codes to messages.
        error_source (int): The error source code (e.g., 100, 200, etc.).
        error_code (str): The specific error code in string form (e.g., "01", "10").

    Returns:
        str: The corresponding error message, or the fallback format.
    """
    # Generate the key for looking up the error message
    key = f"app_error_code_{error_source}_{error_code}"
    
    # Check if the key exists in the error_code_dict
    if key in app_error_messages:
        return app_error_messages[key]
    else:
        # Fallback: return the combination of error_source and error_code
        return f"{error_source}-{error_code}"

def get_error_source_text(error_source):
    """
    Retrieve the error message based on the error source and error code.

    Args:
        error_code_dict (dict): Dictionary mapping error codes to messages.
        error_source (int): The error source code (e.g., 100, 200, etc.).
        error_code (str): The specific error code in string form (e.g., "01", "10").

    Returns:
        str: The corresponding error message, or the fallback format.
    """
    # Generate the key for looking up the error message
    key = f"app_error_source_{error_source}"
    
    # Check if the key exists in the error_code_dict
    if key in app_error_messages:
        return app_error_messages[key]
    else:
        # Fallback: return the combination of error_source and error_code
        return f"{error_source}"

def extract_error_source(error_code):
    """
    Extract the error source from a single error code.
    Common Go2 error sources are typically in ranges like 100, 200, 300, etc.
    """
    if error_code >= 100000:  # If it's a large number, it might be a complex error code
        return 900  # Special category for complex errors
    return (error_code // 100) * 100  # Round down to nearest hundred

def is_critical_error(error_code_int):
    """
    Determine if an error code represents a critical error that might affect robot stability.
    """
    # Convert to hex for pattern matching
    error_hex = hex(error_code_int)[2:].upper()
    
    # Known critical error patterns
    critical_patterns = [
        '67924D46',  # Balance/stability related error
        '135',       # Possible motor/actuator error
        '10'         # Basic system error
    ]
    
    return error_hex in critical_patterns or error_code_int in [int(p, 16) for p in critical_patterns if all(c in '0123456789ABCDEF' for c in p)]

def handle_error(message):
    """
    Handle the error message, print the time, error source, and error message.
    Detect critical errors that might affect robot stability.

    Args:
        message (dict): The error message containing the data field.
    """
    data = message["data"]
    critical_errors_detected = False

    # Handle both single error codes and error tuples
    if not isinstance(data, list):
        data = [data]

    for error in data:
        try:
            # If error is a tuple/list with 3 elements
            if isinstance(error, (list, tuple)) and len(error) == 3:
                timestamp, error_source, error_code_int = error
                readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            else:
                # If error is just an error code
                error_code_int = error
                error_source = 0  # Default error source
                readable_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

            # Check if this is a critical error
            if is_critical_error(error_code_int):
                critical_errors_detected = True
                logging.warning(f"CRITICAL ERROR DETECTED: {error_code_int}")

            error_source_text = get_error_source_text(error_source)
            error_code_hex = integer_to_hex_string(error_code_int)
            error_code_text = get_error_code_text(error_source, error_code_hex)

            severity = "🚨 CRITICAL ERROR" if is_critical_error(error_code_int) else "⚠️ Error"
            print(f"\n{severity} Received from Go2:\n"
                f"🕒 Time:          {readable_time}\n"
                f"🔢 Error Source:  {error_source_text}\n"
                f"❗ Error Code:    {error_code_text}\n"
                f"🔍 Raw Code:     {error_code_int}")

        except Exception as e:
            logging.error(f"Failed to process error: {error}")
            logging.error(f"Error details: {str(e)}")

    return critical_errors_detected
