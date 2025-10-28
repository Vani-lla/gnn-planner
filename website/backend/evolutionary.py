import numpy as np
from backend.models import Requirement
from backend.helpers import *

REQUIREMENTS = Requirement.objects.filter(req_set=12)
REQ_SET = REQUIREMENTS[0].req_set
VALIDATION_HOURS = list(map(lambda req: req.hours, REQUIREMENTS))

BLOCK_LIST, BLOCK_VAL = generate_blocks(REQUIREMENTS, REQ_SET, VALIDATION_HOURS)

population = initialize_population(2, BLOCK_VAL)

