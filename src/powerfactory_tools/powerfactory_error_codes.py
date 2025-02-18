# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2025.
# :license: BSD 3-Clause

import enum


class ErrorCode(enum.IntEnum):
    UNKNOWN_ERROR_OCCURED = 0000

    # Configuration Errors
    CONFIGURATION_CONTAINS_ERRORS = 2000
    CONFIGURATION_FILE_MISSING = 2001
    WINDOWS_CONFIGURATION_ERROR = 2002

    # License Errors
    NO_LICENCE_FOUND_OR_INVALID = 3000
    LICENCE_INVALID = 3001
    LICENCE_REQUIRES_ONLINE_ACCESS = 3002
    FLOATING_LICENCE_NOT_GENERATED_BY_POWERFACTORY = 3003
    ACCESSING_HOT_STANDBY_LICENCE = 3004
    INTERNAL_LICENCE_ERROR = 3005
    FAILED_TO_UPDATE_ACTIVATION_FILE = 3006
    LICENCE_NOT_INCLUDED_IN_ACTIVATION_FILE = 3007
    USING_ENGINE_LICENCE = 3008
    MULTI_USER_DATABASE_NOT_INCLUDED_IN_LICENCE = 3009
    SCRIPTING_AND_AUTOMATION_NOT_INCLUDED_IN_LICENCE = 3010
    ERROR_DURING_LICENCE_THREAD_INITIALIZATION = 3011
    CONNECTION_TO_LICENCE_MODULE_LOST = 3012
    WINDOWS_SERVICE_CODEMETER_NOT_RUNNING = 3013
    LICENCE_SYSTEM_RUNTIME_NOT_INSTALLED = 3014
    FLOATING_LICENCE_EXPIRED = 3015
    CHECKPOINT_LICENCE_REQUIRES_UPDATE = 3016
    SELECTED_LICENCE_EXPIRED = 3017
    USER_MAXIMUM_OF_LICENCE_REACHED = 3018
    LICENCE_BECAME_INVALID = 3019

    # Database Errors
    DATABASE_INIT_REJECTED = 4000
    DATABASE_MIGRATION_FAILED = 4001
    DATABASE_ALREADY_ACCESSED = 4002
    DATABASE_REPAIR_REJECTED = 4003
    DATABASE_CONTAINS_FUTURE_RECORDS = 4004
    DATABASE_CANNOT_BE_READ = 4005
    DATABASE_MIGRATION_REJECTED = 4006
    DATABASE_INVALID_MIGRATION_STATE = 4007
    MIGRATION_FAILED_INCORRECT_PASSWORD = 4008
    STARTING_OFFLINE_SESSION_FAILED = 4009
    INTERNAL_DATABASE_ERROR = 4010
    ID_CONTINGENT_EXHAUSTED = 4011
    ORACLE_CLIENT_LIBRARY_CANNOT_BE_LOADED = 4012
    ERROR_IN_LOCAL_DATABASE = 4013
    CANCELLED_RESET_DATABASE_UNLOCK_KEY = 4014
    EMPTY_ADMINISTRATOR_PASSWORD = 4015
    INCORRECT_DATABASE_UNLOCK_KEY = 4016
    INCORRECT_ADMINISTRATOR_PASSWORD = 4017
    CANNOT_MIGRATE_DATABASE_IN_READ_ONLY_MODE = 4018
    LOCAL_DATABASE_ENCRYPTED = 4019
    DATABASE_MIGRATION_BLOCKED = 4020
    DATABASE_SCHEMA_INVALID = 4021

    # Startup Errors
    USER_COULD_NOT_BE_LOGGED_ON = 5000
    LOGON_RESTRICTED = 5001
    NO_PROFILE_FOUND = 5002
    WORKSPACE_EXPORT_FAILED = 5003
    USER_DID_NOT_CHANGE_PASSWORD = 5004
    ADMINISTRATOR_LOGIN_REQUIRED = 5005
    INITIAL_SETUP_CANCELED = 5006
    USER_DID_NOT_SELECT_WORKING_USER = 5007

    # Runtime Errors
    SIGNAL_BUFFER_SIZE_EXCEEDED = 6000
    FATAL_ERROR_OCCURRED = 6001
    USER_SESSION_TERMINATED = 6002
    APPLICATION_CLOSED_IDLE_SESSION_TIMEOUT = 6003
    APPLICATION_CLOSED_INTERNAL_ERROR = 6004
    MEMORY_ALLOCATION_FAILED = 6005

    # API/Python Errors
    POWERFACTORY_CANNOT_BE_STARTED_AGAIN = 7000
    FUNCTION_CALLED_WITH_INVALID_ARGUMENT = 7001
