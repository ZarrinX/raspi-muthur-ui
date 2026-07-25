pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 15, unit: 'MINUTES')
    }

    environment {
        PI_USER           = 'zrice'
        PI_HOST           = '10.64.32.101'
        PI_DEPLOY_PATH    = '/opt/raspi-muthur-ui'
        SERVICE_NAME      = 'raspi-muthur-ui'
        SERVICE_NETWORK   = 'raspi-muthur-ui-network'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'pi-ssh-key', keyFileVariable: 'SSH_KEY')]) {
                    sh '''
                        rsync -avz --delete \
                            -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
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
                withCredentials([sshUserPrivateKey(credentialsId: 'pi-ssh-key', keyFileVariable: 'SSH_KEY')]) {
                    sh """
                        ssh -i \$SSH_KEY -o StrictHostKeyChecking=no ${PI_USER}@${PI_HOST} '
                            cd ${PI_DEPLOY_PATH} &&
                            python3 -m venv --system-site-packages --clear venv &&
                            venv/bin/pip install --upgrade pip --quiet &&
                            venv/bin/pip install -r requirements.txt --quiet
                        '
                    """
                }
            }
        }

        stage('Install Service Units') {
            steps {
                // Copy both service unit files to systemd and reload the daemon.
                // Requires passwordless sudo for the commands below on the Pi.
                // Add to /etc/sudoers on the Pi:
                //   zrice ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload, /bin/systemctl enable *, /bin/systemctl restart *
                withCredentials([sshUserPrivateKey(credentialsId: 'pi-ssh-key', keyFileVariable: 'SSH_KEY')]) {
                    sh """
                        ssh -i \$SSH_KEY -o StrictHostKeyChecking=no ${PI_USER}@${PI_HOST} '
                            sudo cp ${PI_DEPLOY_PATH}/${SERVICE_NAME}.service /etc/systemd/system/ &&
                            sudo cp ${PI_DEPLOY_PATH}/${SERVICE_NETWORK}.service /etc/systemd/system/ &&
                            sudo systemctl daemon-reload &&
                            sudo systemctl enable ${SERVICE_NAME} &&
                            sudo systemctl enable ${SERVICE_NETWORK}
                        '
                    """
                }
            }
        }

        stage('Restart Services') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'pi-ssh-key', keyFileVariable: 'SSH_KEY')]) {
                    sh "ssh -i \$SSH_KEY -o StrictHostKeyChecking=no ${PI_USER}@${PI_HOST} 'sudo systemctl restart ${SERVICE_NAME} && sudo systemctl restart ${SERVICE_NETWORK}'"
                }
            }
        }
    }

    post {
        failure {
            echo 'Deployment to TARS (10.64.32.101) failed — previous service version is still running.'
        }
        success {
            echo 'raspi-muthur-ui deployed successfully to TARS (10.64.32.101).'
        }
    }
}
