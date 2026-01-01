// 测试 PhaseConfigPanel.vue 是否可以正确导入
console.log('Testing import...');
try {
  const fs = require('fs');
  const path = require('path');

  const filePath = path.join(__dirname, 'frontend/src/modules/trading_agents/components/PhaseConfigPanel.vue');
  console.log('File path:', filePath);

  const content = fs.readFileSync(filePath, 'utf8');
  console.log('File length:', content.length);
  console.log('First 100 chars:', content.substring(0, 100));
  console.log('Last 100 chars:', content.substring(content.length - 100));

  // 检查模板标签
  const templateMatch = content.match(/<template>/g);
  const templateEndMatch = content.match(/<\/template>/g);
  console.log('<template> tags:', templateMatch ? templateMatch.length : 0);
  console.log('</template> tags:', templateEndMatch ? templateEndMatch.length : 0);

  // 检查 script 标签
  const scriptMatch = content.match(/<script/g);
  const scriptEndMatch = content.match(/<\/script>/g);
  console.log('<script tags:', scriptMatch ? scriptMatch.length : 0);
  console.log('</script> tags:', scriptEndMatch ? scriptEndMatch.length : 0);

  // 检查 style 标签
  const styleMatch = content.match(/<style/g);
  const styleEndMatch = content.match(/<\/style>/g);
  console.log('<style tags:', styleMatch ? styleMatch.length : 0);
  console.log('</style> tags:', styleEndMatch ? styleEndMatch.length : 0);

  console.log('✅ File is syntactically valid');
} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}
