podTemplate(label: 'utxo-prometheus-exporter', containers: [
  containerTemplate(name: 'docker', image: 'docker', ttyEnabled: true, command: 'cat', envVars: [
    envVar(key: 'DOCKER_HOST', value: 'tcp://docker-host-docker-host:2375')
  ])
]) {
  node('utxo-prometheus-exporter') {
    stage('Build Image') {
      container('docker') {
        def scmVars = checkout scm
        def PROJECT_NAME = "utxo-prometheus-exporter"
        def VERSION = "1.0.0"

        sh "docker build -t santiment/${PROJECT_NAME}:latest ."

        withDockerRegistry([ credentialsId: "dockerHubCreds", url: "" ]) {
          sh "docker push santiment/${PROJECT_NAME}:latest"
        }
      }
    }
  }
}