@echo off
REM By default it is configured for LM Studio running locally. Uncomment and set API key to use Chat-GPT or other services. More at https://platform.openai.com/docs/api-reference/chat/create
REM SET OPENAI_API_BASE=https://api.openai.com/v1
REM SET OPENAI_API_KEY=xxxxxxxxxxxxxxx
REM SET OPENAI_API_MODEL=gpt-4o
REM SET RETRY_COUNT=0
REM SET SERVER_PORT=8124
REM SET NOVELAI_DEBUG=True

REM Uncomment the following line to generate longer novel outlines
REM SET NOVELAI_TEMPLATES_DIR=templates/alt,templates

REM
@echo off
REM Check if a parameter was passed to the batch file
if "%1"=="" (
    REM No parameter was provided. Start server and open browser.
    python main.py start --inbrowser
) else (
    REM Parameter provided: %1
    REM Execute commands based on the input parameter
    python main.py %*
)
