pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 15, unit: 'MINUTES')
    }

    environment {
        // Update these to match the Pi's hostname/IP and deploy user.
        // The 'pi-ssh-key' credential must be configured in Jenkins as an
        // SSH Username with private key credential.
        PI_USER        = 'zrice'
        PI_HOST        = 'raspberrypi.local'
        PI_DEPLOY_PATH = '/opt/raspi-muthur-ui'
        SERVICE_NAME   = 'raspi-muthur-ui'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Deploy') {
            steps {
                sshagent(credentials: ['pi-ssh-key']) {
                    sh '''
                        rsync -avz --delete \
                            --exclude='.git' \
                            --exclude='venv' \
                            --exclude='__pycache__' \
                            --exclude='*.pyc' \
                            . ${PI_USER}@${PI_HOST}:${PI_DEPLOY_PATH}/
                    '''
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                sshagent(credentials: ['pi-ssh-key']) {
                    sh """
                        ssh ${PI_USER}@${PI_HOST} '
                            cd ${PI_DEPLOY_PATH} &&
                            python3 -m venv venv &&
                            venv/bin/pip install --upgrade pip --quiet &&
                            venv/bin/pip install -r requirements.txt --quiet
                        '
                    """
                }
            }
        }

        stage('Restart Service') {
            steps {
                // Requires passwordless sudo for systemctl restart on the Pi.
                // Add to /etc/sudoers on the Pi:
                //   zrice ALL=(ALL) NOPASSWD: /bin/systemctl restart raspi-muthur-ui
                sshagent(credentials: ['pi-ssh-key']) {
                    sh "ssh ${PI_USER}@${PI_HOST} 'sudo systemctl restart ${SERVICE_NAME}'"
                }
            }
        }
    }

    post {
        failure {
            echo 'Deployment failed — previous service version is still running.'
        }
        success {
            echo 'raspi-muthur-ui deployed successfully.'
        }
    }
}
