# Deployment Guide (AWS Free Tier)

This guide explains how to deploy **Project Harvey** on an AWS EC2 instance using the Free Tier (t2.micro or t3.micro).

## ⚠️ Important Warning regarding Memory
The AWS Free Tier instance (t2.micro) only has **1 GB of RAM**.
Since this project uses **PyTorch** and AI models, it requires more memory than that.
**solution:** We will create a **4GB Swap File** (uses hard disk as RAM).
*Result:* It will run, but it might be slightly slower than your local machine.

## Step 1: Launch EC2 Instance
1.  Log in to AWS Console.
2.  Go to **EC2** -> **Launch Instance**.
3.  **Name**: `ProjectHarvey-Server`.
4.  **OS Image**: Ubuntu Server 24.04 LTS (Free Tier Eligible).
5.  **Instance Type**: `t2.micro` (or `t3.micro` if available in free tier).
6.  **Key Pair**: Create a new key pair (e.g., `harvey-key`), download the `.pem` file.
7.  **Network Settings**:
    -   Allow SSH (Port 22) from Anywhere (or My IP).
    -   Allow HTTP (Port 80) and Custom TCP (Port 8000) from Anywhere.
8.  **Storage**: Set to **20 GB** (Default is 8GB, which is too small for Docker images + AI models). 30GB is free tier limit.
9.  **Launch Instance**.

## Step 2: Connect to Instance
Open your terminal (where your `.pem` file is):
```bash
# Set permissions
chmod 400 harvey-key.pem

# Connect (replace 1.2.3.4 with your Instance Public IP)
ssh -i "harvey-key.pem" ubuntu@1.2.3.4
```

## Step 3: Install Docker & Create Swap
Run these commands inside the EC2 server:

### A. Increase Memory (Swap)
```bash
# Create 4GB swap file
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
# Make it permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### B. Install Docker
```bash
# Update and install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
# Allow running docker without sudo
sudo usermod -aG docker $USER
```
*Logout and log back in for docker permissions to take effect.*
```bash
exit
# Reconnect
ssh -i "harvey-key.pem" ubuntu@1.2.3.4
```

## Step 4: Deploy the Application
1.  **Download Configurations**:
    You need two files on the server: `docker-compose.release.yml` and `.env`.
    You can copy them from your machine using `scp`, or just create them:
    
    ```bash
    # Create docker-compose file
    nano docker-compose.yml
    # (Paste the content of your docker-compose.release.yml here)
    # (Press Ctrl+O, Enter, Ctrl+X to save)
    ```

2.  **Create .env file**:
    ```bash
    nano .env
    # (Paste your GROQ_API_KEY=..., DB details, etc.)
    # (Press Ctrl+O, Enter, Ctrl+X to save)
    ```

3.  **Start the App**:
    ```bash
    docker compose up -d
    ```

## Step 5: Access the App
1.  Go to your AWS EC2 Console.
2.  Find the **Security Group** for your instance.
3.  Edit Inbound Rules -> Add Rule -> Custom TCP -> Port **8000** -> Source `0.0.0.0/0`.
4.  Visit: `http://<YOUR-EC2-PUBLIC-IP>:8000`

## Updates
To update the app when you push a new image:
```bash
docker compose pull
docker compose up -d
```
