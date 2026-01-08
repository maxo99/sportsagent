#!/bin/bash
# Container entrypoint script for SportsAgent

set -e

# Default mode is API
MODE="${SPORTSAGENT_MODE:-api}"

case "$MODE" in
    "api")
        echo "Starting SportsAgent API server..."
        exec uvicorn sportsagent.api:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}
        ;;
    "cli")
        echo "Starting SportsAgent CLI..."
        # Pass any additional arguments to sportsagent CLI
        exec sportsagent "$@"
        ;;
    "help"|"-h"|"--help")
        echo "SportsAgent Container Entrypoint"
        echo ""
        echo "Environment Variables:"
        echo "  SPORTSAGENT_MODE    Set to 'api' (default) or 'cli'"
        echo "  API_HOST           API server host (default: 0.0.0.0)"
        echo "  API_PORT           API server port (default: 8000)"
        echo ""
        echo "Usage:"
        echo "  docker run sportsagent                    # Start API server"
        echo "  SPORTSAGENT_MODE=cli docker run sportsagent chat \"your prompt\""
        echo "  SPORTSAGENT_MODE=cli docker run sportsagent chat --auto-approve"
        exit 0
        ;;
    *)
        echo "Error: Unknown mode '$MODE'. Use 'api' or 'cli'."
        echo "Set SPORTSAGENT_MODE=help for usage information."
        exit 1
        ;;
esac