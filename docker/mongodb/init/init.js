// MongoDB 初始化脚本
// 创建应用数据库和初始用户

// 切换到应用数据库
db = db.getSiblingDB('tradingagents');

// 创建应用用户
db.createUser({
  user: 'tradingagents_user',
  pwd: 'tradingagents_password',
  roles: [
    {
      role: 'readWrite',
      db: 'tradingagents'
    }
  ]
});

// 创建初始集合和索引
// 用户集合
db.createCollection('users');
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "created_at": 1 });

// 系统配置集合
db.createCollection('system_configs');
db.system_configs.createIndex({ "key": 1 }, { unique: true });

// 事件日志集合
db.createCollection('event_logs');
db.event_logs.createIndex({ "timestamp": 1 });
db.event_logs.createIndex({ "event_type": 1 });

// 模块状态集合
db.createCollection('module_states');
db.module_states.createIndex({ "module_name": 1 }, { unique: true });

// 插入初始系统配置
db.system_configs.insertMany([
  {
    key: "system_version",
    value: "1.0.0",
    description: "系统版本",
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    key: "maintenance_mode",
    value: false,
    description: "维护模式开关",
    created_at: new Date(),
    updated_at: new Date()
  }
]);

print('MongoDB initialization completed successfully!');