
import logging

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = xrange(30, 38)

# Sequences 
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

COLORS = {
    'CRITICAL': MAGENTA, # level 50
    'ERROR': RED, # level 40
    'WARNING': CYAN, # level 30
    'INFO': GREEN, # level 20
    'DEBUG': BLUE, # level 10
}

class ColorFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        # can't do super(...) here because Formatter is an old school class
        logging.Formatter.__init__(self, *args, **kwargs)

    def format(self, record):
        """
        Changes record's levelname to use with COLORS enum
        """
        
        levelname = record.levelname
        start = COLOR_SEQ % (COLORS[levelname])
        def_record = logging.Formatter.format(self, record)
        end = RESET_SEQ
        
        colored_record = start + def_record + end
        return colored_record

logging.ColorFormatter = ColorFormatter
