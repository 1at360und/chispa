"""Allow running as: python -m chispa"""

from .cli import main
import sys

sys.exit(main())
