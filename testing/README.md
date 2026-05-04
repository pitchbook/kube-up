# Local development

## Setup

1. Install [kubectl](https://kubernetes.io/docs/reference/kubectl/), [helm](https://helm.sh/), [minikube](https://minikube.sigs.k8s.io/docs/), and [skaffold](https://skaffold.dev/)
2. Execute `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts && helm repo update` to add Prometheus Community Helm repo
3. Execute `minikube start` to start a Minikube cluster

## Running Stack

Execute `skaffold dev` to perform Helm installs and apply the test `KubeUpCheck` CRD. The Kube Up Manager will see the new resource and create the corresponding `Cronjob` and `KubeUpState`. At the next 5-minute interval the synthetic check will run and update the KubeUpState resource, with metrics available from the API.
