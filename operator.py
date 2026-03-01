import kopf
import kubernetes.client
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone

@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    kubernetes.config.load_incluster_config() # Use in-cluster config when running inside Kubernetes
    print("FinOps Operator Started: Listening for sleep schedule annotations...")

@kopf.timer('v1', 'namespaces', interval=60.0)
def check_sleep_schedule(spec, name, annotations, logger, **kwargs):
    # 1. Check if our FinOps annotation exists on this namespace
    schedule = annotations.get('finops-operator/sleep-schedule')
    if not schedule:
        return # Skip namespaces without the annotation
    
    # 2. Parse the time (e.g., "19:00-08:00")
    try:
        sleep_str, wake_str = schedule.split('-')
        # Convert strings to Python Time objects
        sleep_time = datetime.strptime(sleep_str, "%H:%M").time()
        wake_time = datetime.strptime(wake_str, "%H:%M").time()
    except ValueError:
        logger.error(f"Invalid schedule format in namespace {name}. Use HH:MM-HH:MM")
        return

    # 3. Time checking logic (Handles overnight schedules like 19:00 to 08:00)
    # Note: All times are in UTC for consistency across systems. To use local time,
    # change to: datetime.now().astimezone().time() or import pytz for specific timezones.
    now = datetime.now(tz=timezone.utc).time()
    if sleep_time < wake_time:
        is_sleep_time = sleep_time <= now <= wake_time
    else: # Overnight
        is_sleep_time = now >= sleep_time or now <= wake_time

    apps_api = kubernetes.client.AppsV1Api()
    core_api = kubernetes.client.CoreV1Api()

    # 4. Fetch Workloads (Gathering Deployments & StatefulSets)
    workloads = []
    try:
        # Filter by label selector
        def should_scale(obj, label_key="finops-operator/scalable"):
            labels = obj.metadata.labels or {}
            return labels.get(label_key) == "true"
        
        # We store a tuple: (Kind, ResourceObject, ApiPatchFunction)
        deployments = apps_api.list_namespaced_deployment(name).items
        deployments = [d for d in deployments if should_scale(d)]
        workloads.extend([("Deployment", obj, apps_api.patch_namespaced_deployment) for obj in deployments])
        
        statefulsets = apps_api.list_namespaced_stateful_set(name).items
        statefulsets = [s for s in statefulsets if should_scale(s)]
        workloads.extend([("StatefulSet", obj, apps_api.patch_namespaced_stateful_set) for obj in statefulsets])
    except ApiException as e:
        logger.error(f"Error fetching workloads in {name}: {e}")
        return

    # 5. The Unified Scaling Engine (for Deployments & StatefulSets)
    for kind, obj, patch_function in workloads:
        obj_name = obj.metadata.name
        current_replicas = obj.spec.replicas or 0  # Handle None by defaulting to 0
        obj_annotations = obj.metadata.annotations or {}

        # --- EXCLUSION BLOCK ---
        # If a developer explicitly excluded this workload, skip it entirely
        if obj_annotations.get('finops-operator/exclude') == 'true':
            logger.info(f"Ignoring {kind} '{obj_name}': Exclusion annotation found.")
            continue
        # -----------------------

        if is_sleep_time and current_replicas > 0:
            logger.info(f"Sleeping {kind}: {obj_name} -> 0")
            patch = {
                "metadata": {"annotations": {"finops-operator/original-replicas": str(current_replicas)}},
                "spec": {"replicas": 0}
            }
            try:
                patch_function(obj_name, name, patch)
            except ApiException as e:
                logger.error(f"Failed to sleep {kind} {obj_name}: {e}")
                
        elif not is_sleep_time and current_replicas == 0 and obj_annotations.get('finops-operator/original-replicas'):
            original_replicas = int(obj_annotations.get('finops-operator/original-replicas'))
            logger.info(f"Waking {kind}: {obj_name} -> {original_replicas}")
            # Restore replicas and clean up the temporary annotation
            patch = {
                "spec": {"replicas": original_replicas},
                "metadata": {"annotations": {"finops-operator/original-replicas": None}}  # None removes the annotation
            }
            try:
                patch_function(obj_name, name, patch)
            except ApiException as e:
                logger.error(f"Failed to wake {kind} {obj_name}: {e}")

    # 6. Iterate through Pods (Audit/Logging)
    try:
        pods = core_api.list_namespaced_pod(name)
        running_pods = sum(1 for pod in pods.items if pod.status.phase == "Running")
                
        if is_sleep_time and running_pods > 0:
            logger.warning(f"Audit: Namespace {name} still has {running_pods} running pods during sleep window! (Check exclusions or rogue pods)")
            
    except ApiException as e:
        logger.error(f"Pod error in {name}: {e}")