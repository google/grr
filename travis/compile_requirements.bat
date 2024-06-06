
set DIR=%~dp0

set OUT_FOLDER="requirements"


mkdir "%OUT_FOLDER%"

python -m pip install --require-hashes -r "%DIR%\base_tooling_requirements.txt"

python -m piptools compile --generate-hashes -o "%OUT_FOLDER%\windows-requirements.txt"^
    "%DIR%\..\api_client\python\requirements.in"^
    "%DIR%\..\grr\core\requirements.in"^
    "%DIR%\..\grr\server\requirements.in"^
    "%DIR%\..\grr\proto\requirements.in"^
    "%DIR%\..\grr\client\requirements.in"^
    "%DIR%\..\grr\client\requirements_win.in"^
    "%DIR%\..\grr\client_builder\requirements.in"^
    "%DIR%\..\grr\test\requirements.in"


