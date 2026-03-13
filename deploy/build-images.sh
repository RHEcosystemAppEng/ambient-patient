#!/bin/bash
set -euo pipefail

NAMESPACE=${NAMESPACE:-ambient-patient}
REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
BUILD_TARGET="${1:-all}"

echo "Namespace: $NAMESPACE"
echo "Repo: $REPO_ROOT"
echo "Target: $BUILD_TARGET"

# Check if logged in
if ! oc whoami &> /dev/null; then
    echo "ERROR: Not logged in to OpenShift. Run 'oc login' first."
    exit 1
fi

# Create namespace if needed
oc project $NAMESPACE 2>/dev/null || oc new-project $NAMESPACE

# agent backend > app-server
build_app_server() {
    # Agent Backend
    cd "$REPO_ROOT/agent"

    echo "Building Agent Backend > App Server"
    if ! oc get bc app-server &>/dev/null; then
        oc new-build --name=app-server --binary --strategy=docker || { echo "ERROR: Failed to create BuildConfig for App Server"; exit 1; }
    fi
    oc start-build app-server --from-dir=. --follow || { echo "ERROR: App Server build failed"; exit 1; }
}

# ace_controller > pipeline (python-app in docker-compose)
build_ace_controller_pipeline() {
    # Ace Controller
    cd "$REPO_ROOT/ace-controller-voice-interface"

    echo "Building Ace Controller > Pipeline"
    if ! oc get bc ace-controller-pipeline &>/dev/null; then
        oc new-build --name=ace-controller-pipeline --binary --strategy=docker || { echo "ERROR: Failed to create BuildConfig for Ace Controller Pipeline"; exit 1; }
    fi
    oc patch bc ace-controller-pipeline --type=merge -p '{"spec":{"strategy":{"dockerStrategy":{"dockerfilePath":"Dockerfile-python-app"}}}}' || true
    oc start-build ace-controller-pipeline --from-dir=. --follow || { echo "ERROR: Ace Controller Pipeline build failed"; exit 1; }
}

# ace_controller > ui-app (ui-app in docker-compose)
build_ace_controller_ui() {
    cd "$REPO_ROOT/ace-controller-voice-interface"

    echo "Building Ace Controller > UI App"
    if ! oc get bc ace-controller-ui &>/dev/null; then
        oc new-build --name=ace-controller-ui --binary --strategy=docker || { echo "ERROR: Failed to create BuildConfig for Ace Controller UI"; exit 1; }
    fi
    oc patch bc ace-controller-ui --type=merge -p '{"spec":{"strategy":{"dockerStrategy":{"dockerfilePath":"Dockerfile-webrtc-ui"}}}}' || true
    oc start-build ace-controller-ui --from-dir=. --follow || { echo "ERROR: Ace Controller UI build failed"; exit 1; }
}

case "$BUILD_TARGET" in
    app-server)   build_app_server ;;
    ace-controller-pipeline)   build_ace_controller_pipeline ;;
    ace-controller-ui)   build_ace_controller_ui ;;
    all)
        build_app_server
        build_ace_controller_pipeline
        build_ace_controller_ui
        ;;
    *)
        echo "ERROR: Unknown target '$BUILD_TARGET'. Use: app-server, ace-controller-pipeline, ace-controller-ui, or all (default)."
        exit 1
        ;;
esac

echo ""
echo "✓ Build(s) completed successfully!"
echo ""
echo "View images: oc get imagestreams"