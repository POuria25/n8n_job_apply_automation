-- Registers one applicant. Copy this file, replace every value, and run it
-- once after db/schema.sql. Every value below is fictional.
--
-- chat_id       the applicant's private Telegram chat ID
-- *_file        paths as seen inside the n8n container (./assets is mounted at /data/assets)
-- daily_limit   maximum emails per day for this applicant

INSERT INTO applicants (chat_id, sender_name, phone,
                        skeleton_file, email_sample_file, cv_file, daily_limit)
VALUES (123456789, 'Camille Exemple', NULL,
        '/data/assets/letter_skeleton.tex',
        '/data/assets/email_sample.txt',
        '/data/assets/cv.pdf',
        10);
