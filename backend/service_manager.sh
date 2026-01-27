#! /bin/bash
# Wrapper script for VLM Services (Gateway & Inference)

echo "=== VLM Service Manager ==="

if ! command -v systemctl &> /dev/null; then
    echo "Error: systemctl not found."
    exit 1
fi

USAGE="Usage: $0 {start|stop|restart|status|logs} [gateway|inference|all]"

ACTION=$1
TARGET=${2:-gateway} # Default to gateway if not specified

if [ -z "$ACTION" ]; then
    echo "$USAGE"
    exit 1
fi

handle_service() {
    local service_name=$1
    local action=$2
    
    case "$action" in
        start)
            echo "Starting $service_name..."
            sudo systemctl start $service_name
            ;;
        stop)
            echo "Stopping $service_name..."
            sudo systemctl stop $service_name
            ;;
        restart)
            echo "Restarting $service_name..."
            sudo systemctl restart $service_name
            ;;
        status)
            sudo systemctl status $service_name --no-pager
            ;;
        logs)
            sudo journalctl -u $service_name -f
            ;;
        *)
            echo "Invalid action: $action"
            exit 1
            ;;
    esac
}

case "$TARGET" in
    gateway)
        handle_service "vlm-backend" "$ACTION" # Keeping original name for Gateway
        ;;
    inference)
        handle_service "vlm-inference" "$ACTION"
        ;;
    all)
        if [ "$ACTION" == "logs" ]; then
            echo "Cannot follow logs for multiple services. Choose 'gateway' or 'inference'."
            exit 1
        fi
        handle_service "vlm-inference" "$ACTION"
        handle_service "vlm-backend" "$ACTION"
        ;;
    *)
        echo "Invalid target: $TARGET. Use 'gateway', 'inference', or 'all'."
        exit 1
        ;;
esac
