-- 云岫茶坊 AI 茶叶销售系统数据库初始化脚本

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ai_customer_service DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ai_customer_service;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 会话表
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP NULL,
    message_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 消息表
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant', 'system') NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 附件表
CREATE TABLE IF NOT EXISTS attachments (
    id VARCHAR(36) PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    INDEX idx_message_id (message_id),
    INDEX idx_file_type (file_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 工单表
CREATE TABLE IF NOT EXISTS tickets (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    status ENUM('pending', 'in_progress', 'resolved', 'closed') DEFAULT 'pending',
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
    category VARCHAR(50),
    assigned_to VARCHAR(36),
    context JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 工单历史表
CREATE TABLE IF NOT EXISTS ticket_history (
    id VARCHAR(36) PRIMARY KEY,
    ticket_id VARCHAR(36) NOT NULL,
    operator_id VARCHAR(36),
    action VARCHAR(50) NOT NULL,
    old_value VARCHAR(100),
    new_value VARCHAR(100),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (operator_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 知识库文档元数据表
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    tags JSON,
    source VARCHAR(200),
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_category (category),
    INDEX idx_is_active (is_active),
    FULLTEXT idx_content (title, content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id VARCHAR(36) PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description VARCHAR(500),
    updated_by VARCHAR(36),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(36),
    details JSON,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_resource (resource_type, resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 电商扩展表 ====================

-- 10. 商品分类表
CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id VARCHAR(36),
    description TEXT,
    icon VARCHAR(200),
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE,
    INDEX idx_parent (parent_id),
    INDEX idx_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. 商品表
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(36) PRIMARY KEY,
    seller_id VARCHAR(36) NOT NULL,
    category_id VARCHAR(36) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2),
    cover_image VARCHAR(500),
    demo_video VARCHAR(500),
    tech_stack JSON,
    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    status ENUM('draft', 'pending', 'published', 'rejected', 'sold_out') DEFAULT 'draft',
    view_count INT DEFAULT 0,
    sales_count INT DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 0.00,
    review_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    INDEX idx_category (category_id),
    INDEX idx_seller (seller_id),
    INDEX idx_status (status),
    INDEX idx_price (price),
    INDEX idx_rating (rating),
    INDEX idx_sales (sales_count),
    FULLTEXT idx_search (title, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. 商品图片表
CREATE TABLE IF NOT EXISTS product_images (
    id VARCHAR(36) PRIMARY KEY,
    product_id VARCHAR(36) NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product (product_id),
    INDEX idx_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. 商品文件表
CREATE TABLE IF NOT EXISTS product_files (
    id VARCHAR(36) PRIMARY KEY,
    product_id VARCHAR(36) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product (product_id),
    INDEX idx_file_type (file_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. 购物车表
CREATE TABLE IF NOT EXISTS cart_items (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_product (user_id, product_id),
    INDEX idx_user (user_id),
    INDEX idx_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. 订单表
CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(36) PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    buyer_id VARCHAR(36) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'paid', 'delivered', 'completed', 'cancelled', 'refunded') DEFAULT 'pending',
    payment_method VARCHAR(50),
    payment_time TIMESTAMP NULL,
    delivery_time TIMESTAMP NULL,
    completion_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users(id),
    INDEX idx_buyer (buyer_id),
    INDEX idx_status (status),
    INDEX idx_order_no (order_no),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 16. 订单明细表
CREATE TABLE IF NOT EXISTS order_items (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    seller_id VARCHAR(36) NOT NULL,
    product_title VARCHAR(200) NOT NULL,
    product_cover VARCHAR(500),
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (seller_id) REFERENCES users(id),
    INDEX idx_order (order_id),
    INDEX idx_product (product_id),
    INDEX idx_seller (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 17. 交易记录表
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL,
    transaction_no VARCHAR(100) UNIQUE NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'success', 'failed', 'refunded') DEFAULT 'pending',
    payment_time TIMESTAMP NULL,
    refund_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    INDEX idx_order (order_id),
    INDEX idx_transaction_no (transaction_no),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 18. 评价表
CREATE TABLE IF NOT EXISTS reviews (
    id VARCHAR(36) PRIMARY KEY,
    order_item_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    buyer_id VARCHAR(36) NOT NULL,
    seller_id VARCHAR(36) NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    content TEXT,
    images JSON,
    reply TEXT,
    reply_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_item_id) REFERENCES order_items(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (buyer_id) REFERENCES users(id),
    FOREIGN KEY (seller_id) REFERENCES users(id),
    INDEX idx_product (product_id),
    INDEX idx_buyer (buyer_id),
    INDEX idx_seller (seller_id),
    INDEX idx_rating (rating),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 19. 收藏表
CREATE TABLE IF NOT EXISTS favorites (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_product (user_id, product_id),
    INDEX idx_user (user_id),
    INDEX idx_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 20. 用户浏览历史表
CREATE TABLE IF NOT EXISTS user_browse_history (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    view_duration INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_product_browse (user_id, product_id),
    INDEX idx_user (user_id),
    INDEX idx_product (product_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员用户（密码: admin123，需要在应用中修改）
INSERT INTO users (id, username, password_hash, email, role, is_active) 
VALUES (
    UUID(),
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS.sC9jWu',  -- admin123
    'admin@example.com',
    'admin',
    TRUE
) ON DUPLICATE KEY UPDATE username=username;

-- 插入默认系统配置
INSERT INTO system_config (id, config_key, config_value, description) VALUES
(UUID(), 'llm_temperature', '0.7', 'LLM温度参数'),
(UUID(), 'llm_max_tokens', '2000', 'LLM最大token数'),
(UUID(), 'retrieval_top_k', '3', '知识检索返回数量'),
(UUID(), 'max_concurrent_sessions', '50', '最大并发会话数')
ON DUPLICATE KEY UPDATE config_key=config_key;

-- ==================== 测试数据 ====================

-- 插入测试用户（买家和卖家）
INSERT INTO users (id, username, password_hash, email, role, is_active) VALUES
(UUID(), 'buyer1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS.sC9jWu', 'buyer1@example.com', 'user', TRUE),
(UUID(), 'seller1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS.sC9jWu', 'seller1@example.com', 'user', TRUE),
(UUID(), 'seller2', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS.sC9jWu', 'seller2@example.com', 'user', TRUE)
ON DUPLICATE KEY UPDATE username=username;

-- 插入茶叶商品分类
INSERT INTO categories (id, name, parent_id, description, icon, sort_order) VALUES
(UUID(), '绿茶', NULL, '清香鲜爽、注重嫩度与时令的非发酵茶', 'leaf', 1),
(UUID(), '红茶', NULL, '香甜醇和、适合日常饮用与礼赠的全发酵茶', 'cup', 2),
(UUID(), '乌龙茶', NULL, '香气层次丰富、滋味醇厚的半发酵茶', 'mountain', 3),
(UUID(), '白茶', NULL, '工艺自然、毫香清甜的轻微发酵茶', 'sunny', 4),
(UUID(), '普洱茶', NULL, '越陈越香、口感醇滑的后发酵茶', 'collection', 5),
(UUID(), '花茶', NULL, '茶香与花香融合、清雅怡人的再加工茶', 'flower', 6)
ON DUPLICATE KEY UPDATE name=name;

-- 获取分类ID（用于插入商品）
SET @cat_green = (SELECT id FROM categories WHERE name = '绿茶' LIMIT 1);
SET @cat_black = (SELECT id FROM categories WHERE name = '红茶' LIMIT 1);
SET @cat_oolong = (SELECT id FROM categories WHERE name = '乌龙茶' LIMIT 1);
SET @cat_white = (SELECT id FROM categories WHERE name = '白茶' LIMIT 1);
SET @cat_puer = (SELECT id FROM categories WHERE name = '普洱茶' LIMIT 1);
SET @cat_flower = (SELECT id FROM categories WHERE name = '花茶' LIMIT 1);

-- 获取卖家ID
SET @seller1_id = (SELECT id FROM users WHERE username = 'seller1' LIMIT 1);
SET @seller2_id = (SELECT id FROM users WHERE username = 'seller2' LIMIT 1);

-- 插入茶叶测试商品（价格单位：分）
INSERT INTO products (id, seller_id, category_id, title, description, price, original_price, cover_image, tech_stack, difficulty, status, view_count, sales_count, rating, review_count) VALUES
(UUID(), @seller1_id, @cat_green, '明前特级西湖龙井 250g', '产自浙江杭州核心产区，豆香清雅，茶汤嫩绿明亮，入口鲜爽回甘。建议使用85℃左右水温冲泡。', 26800, 32800, NULL, '["浙江杭州", "豆香", "鲜爽", "炒青绿茶"]', 'easy', 'published', 1834, 326, 490, 186),
(UUID(), @seller1_id, @cat_green, '洞庭碧螺春一级春茶 250g', '产自江苏苏州太湖产区，花果香明显，滋味鲜醇柔和，适合偏爱清香型绿茶的顾客。', 19800, 24800, NULL, '["江苏苏州", "花果香", "鲜醇", "卷曲绿茶"]', 'easy', 'published', 1260, 218, 475, 124),
(UUID(), @seller2_id, @cat_black, '武夷金骏眉特级红茶 250g', '精选福建武夷山原料制作，蜜香与花香协调，滋味甘醇顺滑，适合自饮或礼赠。', 32800, 39800, NULL, '["福建武夷山", "蜜香", "甘醇", "全发酵"]', 'medium', 'published', 2350, 408, 492, 236),
(UUID(), @seller2_id, @cat_oolong, '武夷山大红袍岩茶 250g', '焙火香沉稳，茶汤橙黄明亮，入口醇厚并带有明显岩韵，适合喜欢浓郁耐泡口感的茶友。', 23800, 29800, NULL, '["武夷岩茶", "焙火香", "岩韵", "半发酵"]', 'hard', 'published', 1988, 305, 486, 175),
(UUID(), @seller1_id, @cat_oolong, '安溪铁观音清香型 250g', '产自福建安溪，兰花香清晰，茶汤黄绿明亮，滋味清鲜并带回甘。', 16800, 21800, NULL, '["福建安溪", "兰花香", "清鲜", "半发酵"]', 'medium', 'published', 1568, 287, 478, 146),
(UUID(), @seller1_id, @cat_white, '福鼎白牡丹白茶 300g', '选用福建福鼎春季原料，芽叶舒展，毫香与清甜感突出，茶汤柔和。', 21800, 26800, NULL, '["福建福鼎", "毫香", "清甜", "轻微发酵"]', 'easy', 'published', 1426, 196, 481, 118),
(UUID(), @seller2_id, @cat_puer, '新会陈皮普洱熟茶 357g', '云南普洱熟茶与新会陈皮搭配，陈香与柑香协调，茶汤红浓醇滑。', 29800, 36800, NULL, '["云南勐海", "新会陈皮", "陈香", "后发酵"]', 'hard', 'published', 2248, 364, 488, 203),
(UUID(), @seller1_id, @cat_flower, '横州茉莉银针花茶 250g', '选用广西横州茉莉鲜花多次窨制，花香鲜灵持久，茶汤清亮柔和。', 13800, 17800, NULL, '["广西横州", "茉莉花香", "清雅", "多次窨制"]', 'easy', 'published', 1186, 246, 472, 132)
ON DUPLICATE KEY UPDATE title=title;
