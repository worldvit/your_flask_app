-- 10.10.8.4
-- sudo -i
-- apt update
-- apt install mariadb-server mariadb-client -y

-- 50-server.conf 파일 수정
sudo vi /etc/mysql/mariadb.conf.d/50-server.cnf
bind-address = 0.0.0.0

systemctl restart mariadb

sudo mysql -u root -p
CREATE DATABASE flask_auth_db;
CREATE USER 'flask_user'@'10.0.8.3' IDENTIFIED BY 'P@ssw0rd';
GRANT ALL PRIVILEGES ON flask_auth_db.* TO 'flask_user'@'10.0.8.3';
FLUSH PRIVILEGES;

-- users 테이블 생성
USE flask_auth_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- board 테이블 생성
USE flask_auth_db;

CREATE TABLE board (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- comments 테이블 생성
CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    board_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (board_id) REFERENCES board(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

EXIT;


-- 10.10.8.3
sudo apt update

sudo apt install apache2 libapache2-mod-wsgi-py3
sudo a2enmod wsgi

sudo apt install python3.12 python3.12-venv python3.12-dev # Install Python 3.12 and development headers

cd /var/www/html/
sudo git clone https://github.com/worldvit/your_flask_app.git

sudo chown -R www-data: /var/www/html/your_flask_app

cd /etc/apache2/sites-enabled/
sudo rm /etc/apache2/sites-enabled/000-default.conf

cd /etc/apache2/sites-available

cat<<EOF>flask_auth.conf
WSGIPythonHome /var/www/html/your_flask_app/venv
WSGIPythonPath /var/www/html/your_flask_app

<VirtualHost *:80>
    ServerName 10.10.8.3
    ServerAdmin webmaster@localhost
    WSGIScriptAlias / /va기
truncate -s 0 /var/log/apache2/flask_auth_error.log
tail -n 100 /var/log/apache2/flask_auth_error.log
