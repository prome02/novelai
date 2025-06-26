@echo off
REM By default it is configured for LM Studio running locally. Uncomment and set API key to use Chat-GPT or other services. More at https://platform.openai.com/docs/api-reference/chat/create
SET OPENAI_API_BASE=https://api.openai.com/v1
REM SET OPENAI_API_KEY=xxxxxxxxxxxxxxx
SET OPENAI_API_MODEL=gpt-4o
SET RETRY_COUNT=0
SET SERVER_PORT=8124
SET NOVELAI_DEBUG=False

REM Uncomment the following line to generate longer novel outlines
REM SET NOVELAI_TEMPLATES_DIR=templates/alt,templates

REM
@echo off
REM Check if a parameter was passed to the batch file
if "%1"=="" (
    REM No parameter was provided. Start server and open browser.
    python main.py start --inbrowser --share
) else (
    REM Parameter provided: %1
    REM Execute commands based on the input parameter
    python main.py %*
)
