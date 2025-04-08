from sensitiveVariables.sensitiveVariables import SensitiveVariables

def get_db_info():
    sensitive_vars = SensitiveVariables()
    return sensitive_vars.database

print(get_db_info())