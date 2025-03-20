#!/usr/bin/env bash

set -e

# TODO: Set to URL of git repo.
PROJECT_GIT_URL='https://github.com/Scottman625/ParkManagementSystem.git'

PROJECT_BASE_PATH='/usr/local/apps/park'

PROJECT_PATH='/usr/local/apps/park/app'

echo "Installing dependencies..."
apt-get update
echo "Hello..."
apt-get install -y python3-dev python3-venv sqlite python3-pip supervisor nginx git

# 處理已存在的目錄
if [ -d "$PROJECT_BASE_PATH" ]; then
    echo "Directory $PROJECT_BASE_PATH already exists"
    echo "Updating existing repository..."
    cd $PROJECT_BASE_PATH
    
    # 檢查是否為 git 倉庫
    if [ -d ".git" ]; then
        # 獲取遠端分支信息
        git fetch origin
        # 獲取當前分支名稱
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD || echo "master")
        echo "Current branch: $CURRENT_BRANCH"
        # 重置到遠端分支的最新狀態
        git reset --hard "origin/$CURRENT_BRANCH"
    else
        echo "Not a git repository. Removing and cloning..."
        cd ..
        rm -rf $PROJECT_BASE_PATH
        git clone $PROJECT_GIT_URL $PROJECT_BASE_PATH
    fi
else
    echo "Creating project directory..."
    mkdir -p $PROJECT_BASE_PATH
    git clone $PROJECT_GIT_URL $PROJECT_BASE_PATH
fi

# 處理虛擬環境
if [ -d "$PROJECT_BASE_PATH/env" ]; then
    echo "Virtual environment already exists"
else
    echo "Creating virtual environment..."
    mkdir -p $PROJECT_BASE_PATH/env
    python3 -m venv $PROJECT_BASE_PATH/env
fi

# 安裝 python3-pip
apt-get install python3-pip

# Install python packages
$PROJECT_BASE_PATH/env/bin/python3 -m pip install -r $PROJECT_BASE_PATH/requirements.txt
$PROJECT_BASE_PATH/env/bin/python3 -m pip install uwsgi

# Run migrations and collectstatic
cd $PROJECT_PATH
$PROJECT_BASE_PATH/env/bin/python3 manage.py migrate
$PROJECT_BASE_PATH/env/bin/python3 manage.py collectstatic --noinput

# Configure supervisor
cp $PROJECT_PATH/deploy/supervisor_profiles_api.conf /etc/supervisor/conf.d/park_profiles_api.conf
supervisorctl reread
supervisorctl update
supervisorctl restart park_profiles_api

# Configure nginx
cp $PROJECT_PATH/deploy/nginx_profiles_api.conf /etc/nginx/sites-available/park_profiles_api.conf
rm /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/park_profiles_api.conf /etc/nginx/sites-enabled/park_profiles_api.conf
systemctl restart nginx.service

echo "DONE! :)"
