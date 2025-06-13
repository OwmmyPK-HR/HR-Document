from flask import current_app

def allowed_file(filename, allowed_extensions_config):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions_config