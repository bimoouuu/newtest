-- Messages à réactions publiés par le bot
CREATE TABLE IF NOT EXISTS reaction_messages (
    message_id    BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    guild_id      BIGINT UNSIGNED NOT NULL,
    channel_id    BIGINT UNSIGNED NOT NULL,
    title         VARCHAR(256)    NOT NULL,
    body          TEXT            NOT NULL,
    single_choice BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Association emoji vers rôle (collation binaire : sinon MariaDB confond certains emojis)
CREATE TABLE IF NOT EXISTS reaction_roles (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT PRIMARY KEY,
    message_id    BIGINT UNSIGNED NOT NULL,
    emoji_key     VARCHAR(64)     CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    emoji_display VARCHAR(128)    NOT NULL,
    role_id       BIGINT UNSIGNED NOT NULL,
    UNIQUE KEY uq_message_emoji (message_id, emoji_key),
    CONSTRAINT fk_reaction_message FOREIGN KEY (message_id)
        REFERENCES reaction_messages (message_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Contenus déjà annoncés, pour ne jamais notifier deux fois
CREATE TABLE IF NOT EXISTS sent_notifications (
    platform   VARCHAR(16)  NOT NULL,
    content_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (platform, content_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- Jetons OAuth des plateformes (TikTok)
CREATE TABLE IF NOT EXISTS oauth_tokens (
    provider      VARCHAR(16) NOT NULL PRIMARY KEY,
    access_token  TEXT        NOT NULL,
    refresh_token TEXT        NOT NULL,
    expires_at    DATETIME    NOT NULL,
    updated_at    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
