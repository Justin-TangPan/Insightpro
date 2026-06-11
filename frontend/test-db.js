const { Client } = require('pg');
require('dotenv').config({ path: '../.env' });

async function testConnection() {
  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: {
      rejectUnauthorized: false
    }
  });

  try {
    console.log('正在尝试连接到:', process.env.DATABASE_URL.replace(/:.*@/, ':****@'));
    await client.connect();
    console.log('✅ 连接成功！');
    const res = await client.query('SELECT NOW()');
    console.log('当前时间:', res.rows[0]);
    await client.end();
  } catch (err) {
    console.error('❌ 连接失败:', err.message);
    console.error('错误详情:', err);
  }
}

testConnection();
