# By default it is configured for LM Studio running locally. Uncomment and set API key to use Chat-GPT or other services. More at https://platform.openai.com/docs/api-reference/chat/create
#export OPENAI_API_BASE=https://api.openai.com/v1
#export OPENAI_API_KEY=xxxxxxxxxxxxxxx
#export OPENAI_API_MODEL=gpt-4o
#export RETRY_COUNT=0
#export SERVER_PORT=8124
#export NOVELAI_DEBUG=True

# Uncommon the following line to generate longer novel outlines
#export NOVELAI_TEMPLATES_DIR=templates/alt,templates

# Usage: my default starts the HTTP server and opens web browser. If any commands are set, it will run those instead

# Check if a parameter was passed
if [ -z "$1" ]; then
    # No parameter was provided.
    python main.py start --inbrowser
else
    # echo "Parameter provided: $1"
    # Execute commands based on the input parameter
    python main.py "$@"
fi
