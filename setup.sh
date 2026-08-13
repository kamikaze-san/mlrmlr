#!/usr/bin/env bash
set -euo pipefail

# No model weights to pre-fetch -- this pipeline uses only the competition's
# provided LLM endpoint for generation and does not self-host any generative
# or embedding model. This step just verifies the pip-installed dependencies
# actually import cleanly, so a packaging problem surfaces here (untimed)
# rather than inside run.sh (timed).

cd "$(dirname "${BASH_SOURCE[0]}")"

python3 -c "
import fitz, pandas, numpy, openpyxl
print('setup.sh: all required packages import cleanly.')
"
