CREATE DATABASE IF NOT EXISTS talentscan_db;
USE talentscan_db;

CREATE TABLE IF NOT EXISTS hr_users (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    first_name     VARCHAR(50)  NOT NULL,
    last_name      VARCHAR(50)  NOT NULL,
    email          VARCHAR(120) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_roles (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidates (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    full_name        VARCHAR(120) NOT NULL,
    email            VARCHAR(120),
    resume_filename  VARCHAR(255),
    job_role_id      INT,
    match_score      INT DEFAULT 0,
    status           ENUM('new','processing','processed','shortlisted','reviewing','rejected') DEFAULT 'new',
    extracted_skills TEXT,
    uploaded_by      INT,
    uploaded_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_role_id) REFERENCES job_roles(id) ON DELETE SET NULL,
    FOREIGN KEY (uploaded_by) REFERENCES hr_users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    action_text VARCHAR(255),
    color       VARCHAR(20) DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES hr_users(id) ON DELETE SET NULL
);

INSERT IGNORE INTO job_roles (id, title, description) VALUES
(1, 'Software Engineer',   'Backend and frontend development roles'),
(2, 'Data Analyst',        'Data analysis and visualization roles'),
(3, 'UI/UX Designer',      'Product design and user experience roles'),
(4, 'Project Manager',     'Project management and coordination roles'),
(5, 'HR Business Partner', 'Human resources generalist roles');
