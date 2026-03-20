#!/bin/bash
# Deploy Ambient Patient app-server with Helm
#
# Helm values for secrets (TURN_*, API keys, Metered, etc.) come only from the environment of this process.
# Export them in your shell, or load a file first, e.g.:
#   set -a && source ace-controller-voice-interface/ace_controller.env && set +a && ./deploy/deploy-app.sh
# Optional: merge deploy/turn-overrides.yaml if that file exists (advanced).

set -euo pipefail

NAMESPACE=${NAMESPACE:-ambient-patient}
RELEASE_NAME=${RELEASE_NAME:-ambient-patient}
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

HELM_TMP_FILES=()
cleanup_helm_tmp() {
    rm -f "${HELM_TMP_FILES[@]}"
}
trap cleanup_helm_tmp EXIT

echo "Deploying Ambient Patient (app-server + full-agent-ui + ace-controller-pipeline)"
echo "Namespace: $NAMESPACE"
echo "Release: $RELEASE_NAME"

if [[ -z "${TURN_SERVER_URL:-}" ]]; then
    echo "Note: TURN_SERVER_URL is unset — static TURN for the Python peer will be empty (export TURN_* before running, or source ace_controller.env as in the script header)."
fi

# Check if logged in
if ! oc whoami &> /dev/null; then
    echo "ERROR: Not logged in to OpenShift. Run 'oc login' first."
    exit 1
fi

echo "Checking if images exist..."
oc get imagestream app-server -n $NAMESPACE &>/dev/null || { echo "ERROR: app-server image not found. Run ./deploy/build-images.sh app-server first"; exit 1; }
oc get imagestream ace-controller-pipeline -n $NAMESPACE &>/dev/null || { echo "ERROR: ace-controller-pipeline image not found. Run ./deploy/build-images.sh ace-controller-pipeline first"; exit 1; }

# Build Helm set args for API keys (optional env vars)
SET_ARGS=(
    --namespace "$NAMESPACE"
    --set "images.namespace=$NAMESPACE"
    --set "namespace=$NAMESPACE"
)
[ -n "${NVIDIA_API_KEY:-}" ] && SET_ARGS+=(--set "appServer.nvidiaApiKey=$NVIDIA_API_KEY")
[ -n "${NGC_API_KEY:-}" ] && SET_ARGS+=(--set "appServer.ngcApiKey=$NGC_API_KEY")
[ -n "${TAVILY_API_KEY:-}" ] && SET_ARGS+=(--set "appServer.tavilyApiKey=$TAVILY_API_KEY")
[ -n "${LANGSMITH_API_KEY:-}" ] && SET_ARGS+=(--set "appServer.langsmithApiKey=$LANGSMITH_API_KEY")
[ -n "${NVIDIA_API_KEY:-}" ] && SET_ARGS+=(--set "aceControllerPipeline.nvidiaApiKey=$NVIDIA_API_KEY")
[ -n "${NGC_API_KEY:-}" ] && SET_ARGS+=(--set "aceControllerPipeline.ngcApiKey=$NGC_API_KEY")
# TURN: use --set-file so $, !, newlines, etc. in credentials are not mangled by the shell or Helm --set
if [ -n "${TURN_SERVER_URL:-}" ]; then
    tf=$(mktemp)
    HELM_TMP_FILES+=("$tf")
    printf '%s' "$TURN_SERVER_URL" >"$tf"
    SET_ARGS+=(--set-file "aceControllerPipeline.turnServerUrl=$tf")
fi
if [ -n "${TURN_USERNAME:-}" ]; then
    tf=$(mktemp)
    HELM_TMP_FILES+=("$tf")
    printf '%s' "$TURN_USERNAME" >"$tf"
    SET_ARGS+=(--set-file "aceControllerPipeline.turnUsername=$tf")
fi
if [ -n "${TURN_PASSWORD:-}" ]; then
    tf=$(mktemp)
    HELM_TMP_FILES+=("$tf")
    printf '%s' "$TURN_PASSWORD" >"$tf"
    SET_ARGS+=(--set-file "aceControllerPipeline.turnPassword=$tf")
fi
[ -n "${METERED_TURN_API_KEY:-}" ] && SET_ARGS+=(--set-string "aceControllerPipeline.meteredTurnApiKey=$METERED_TURN_API_KEY")
[ -n "${METERED_CREDENTIALS_URL:-}" ] && SET_ARGS+=(--set-string "aceControllerPipeline.meteredCredentialsUrl=$METERED_CREDENTIALS_URL")

# Optional values file (prepend so --set in SET_ARGS still wins). Avoid "${empty[@]}" with set -u on bash 3.2 (macOS).
if [[ -f "$SCRIPT_DIR/turn-overrides.yaml" ]]; then
    SET_ARGS=(-f "$SCRIPT_DIR/turn-overrides.yaml" "${SET_ARGS[@]}")
fi

echo "Installing Helm chart..."
helm upgrade --install "$RELEASE_NAME" "$SCRIPT_DIR/ambient-patient" "${SET_ARGS[@]}"

echo ""
echo "✓ Ambient Patient (app-server + full-agent-ui + ace-controller-pipeline) deployed successfully!"
echo ""
echo "Monitor deployment:"
echo "  oc get pods -n $NAMESPACE -w"
echo ""
echo "Full Agent UI (open in browser):"
echo "  https://<host>/full-assistant/"
echo "  Get host: oc get route -n $NAMESPACE -l app.kubernetes.io/component=full-agent-ui -o jsonpath='{.items[0].spec.host}'"
