// MongoDB 初始化脚本
// 创建数据库用户和初始化集合

db = db.getSiblingDB('stock_analysis');

// 创建管理员用户（可选）
// db.createUser({
//   user: 'admin',
//   pwd: 'admin123',
//   roles: [
//     { role: 'readWrite', db: 'stock_analysis' }
//   ]
// });

// 创建初始索引
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ created_at: 1 });
db.user_preferences.createIndex({ user_id: 1 });
db.user_preferences.createIndex({ user_id: 1, key: 1 }, { unique: true });
db.sessions.createIndex({ session_id: 1 }, { unique: true });
db.sessions.createIndex({ user_id: 1 });
db.sessions.createIndex({ expires_at: 1 });

print('MongoDB initialized successfully');
