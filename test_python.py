import sys
import logging

#%% Logging funcs
def logger_setup():
    logger = logging.getLogger('app')
    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create a file handler
    filename = sys.argv[0].split('/')[-1]
    log_file = '/'.join(sys.argv[0].split('/')[:-1]) + '/logs/' + filename.replace('.py','.log')
    file_handler = logging.FileHandler(log_file, 'a+')
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s')

    # Set the formatter for both handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG)

    return logger

logger = logger_setup()

logger.info('Kicked off python script')
