import { useState } from 'react'
import { Card, Button, Row, Col, Typography, Alert, Space, Tag, Divider } from 'antd'
import { globalMessage } from '@/services/http/message-ref'
import { RocketOutlined, ReloadOutlined, StockOutlined } from '@ant-design/icons'
import { useAnalysisSubmit } from '@/features/analysis/hooks/useAnalysisSubmit'
import { useAnalysisProgress } from '@/features/analysis/hooks/useAnalysisProgress'
import StockCodeInput from '@/features/analysis/components/StockCodeInput'
import MarketSelector from '@/features/analysis/components/MarketSelector'
import AnalysisConfigForm from '@/features/analysis/components/AnalysisConfigForm'
import AnalysisProgressBar from '@/features/analysis/components/AnalysisProgressBar'
import AnalysisStepTimeline from '@/features/analysis/components/AnalysisStepTimeline'
import AnalysisResultView from '@/features/analysis/components/AnalysisResultView'
import type { AnalysisConfigFormValues } from '@/features/analysis/components/AnalysisConfigForm'
import { DEFAULT_SELECTED_ANALYSTS } from '@/constants/analysts'
import dayjs from 'dayjs'

const { Title, Text } = Typography

const cardStyle: React.CSSProperties = { background: 'var(--bg-card)', border: 'none' }
const cardHeaderStyle: React.CSSProperties = { borderBottom: '1px solid rgba(255,255,255,0.06)' }

const defaultConfig: AnalysisConfigFormValues = {
  selected_analysts: DEFAULT_SELECTED_ANALYSTS,
  phase2_enabled: true,
  phase2_debate_rounds: 2,
  phase3_enabled: true,
  phase3_debate_rounds: 2,
}

export default function SingleAnalysisPage() {
  const [symbol, setSymbol] = useState('')
  const [market, setMarket] = useState('CN')
  const [config, setConfig] = useState<AnalysisConfigFormValues>({ ...defaultConfig })

  const { submitSingle, loading: submitting, error: submitError, taskId, reset: resetSubmit } = useAnalysisSubmit()
  const { progress, status, currentStep, stepDetail, result, isRunning, error: progressError, isConnected } =
    useAnalysisProgress({ taskId: taskId || undefined })

  const isDisabled = submitting || isRunning

  const handleSubmit = async () => {
    if (!symbol.trim()) {
      globalMessage?.warning('请输入股票代码')
      return
    }
    const success = await submitSingle({
      symbol: symbol.trim(),
      parameters: {
        market_type: market,
        analysis_date: dayjs().format('YYYY-MM-DD'),
        ...config,
        selected_analysts: config.selected_analysts || [],
      },
    })
    if (success) {
      globalMessage?.success('分析任务已提交')
    }
  }

  const handleReset = () => {
    setSymbol('')
    setMarket('CN')
    setConfig({ ...defaultConfig })
    resetSubmit()
  }

  const showResult = result && status === 'completed'
  const showProgress = isRunning || status === 'completed' || status === 'failed' || status === 'cancelled'

  return (
    <div style={{ color: 'var(--text-primary)' }}>
      <Title level={3} style={{ color: 'var(--text-primary)', marginBottom: 24 }}>
        单股分析
      </Title>

      <Row gutter={[24, 24]}>
        {/* 左侧：配置面板 */}
        <Col xs={24} lg={10}>
          <Card
            title={
              <Space>
                <StockOutlined />
                <span>分析配置</span>
              </Space>
            }
            style={cardStyle}
            styles={{ header: cardHeaderStyle }}
          >
            <Space vertical size="middle" style={{ width: '100%' }}>
              {/* 基础信息 */}
              <Row gutter={16}>
                <Col span={10}>
                  <Text style={{ color: 'var(--text-secondary)', fontSize: 13, display: 'block', marginBottom: 6 }}>
                    市场类型
                  </Text>
                  <MarketSelector value={market} onChange={setMarket} disabled={isDisabled} />
                </Col>
                <Col span={14}>
                  <Text style={{ color: 'var(--text-secondary)', fontSize: 13, display: 'block', marginBottom: 6 }}>
                    股票代码
                  </Text>
                  <StockCodeInput
                    value={symbol}
                    onChange={setSymbol}
                    market={market}
                    disabled={isDisabled}
                  />
                </Col>
              </Row>

              <Divider style={{ margin: '4px 0' }} />

              {/* 阶段配置 */}
              <AnalysisConfigForm
                values={config}
                onChange={setConfig}
                disabled={isDisabled}
              />

              {submitError && <Alert message={submitError} type="error" showIcon />}

              {/* 操作按钮 */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 4 }}>
                <Button onClick={handleReset} disabled={isDisabled}>
                  重置
                </Button>
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  loading={submitting}
                  disabled={isRunning}
                  onClick={handleSubmit}
                  style={{
                    background: 'var(--accent-primary)',
                    borderColor: 'var(--accent-primary)',
                    boxShadow: '0 2px 12px rgba(201,169,110,0.2)',
                  }}
                >
                  开始分析
                </Button>
              </div>
            </Space>
          </Card>
        </Col>

        {/* 右侧：进度与结果 */}
        <Col xs={24} lg={14}>
          {showProgress ? (
            <Space vertical size="middle" style={{ width: '100%' }}>
              <Card
                title={<span style={{ color: 'var(--text-primary)' }}>分析进度</span>}
                style={cardStyle}
                styles={{ header: cardHeaderStyle }}
                extra={
                  isConnected ? (
                    <Tag color="success">实时连接中</Tag>
                  ) : isRunning ? (
                    <Tag>连接中...</Tag>
                  ) : null
                }
              >
                <Space vertical size="middle" style={{ width: '100%' }}>
                  <AnalysisProgressBar
                    progress={progress}
                    status={isRunning ? 'active' : status === 'completed' ? 'success' : 'exception'}
                  />
                  <div>
                    <Text strong style={{ color: 'var(--text-primary)' }}>{currentStep || status}</Text>
                    {stepDetail && (
                      <div style={{ color: 'var(--text-secondary)', marginTop: 4 }}>{stepDetail}</div>
                    )}
                  </div>
                  {progressError && <Alert message={progressError} type="error" showIcon />}
                  <AnalysisStepTimeline currentStepName={currentStep} />
                  {!isRunning && status !== 'completed' && (
                    <Button icon={<ReloadOutlined />} onClick={handleReset}>重新分析</Button>
                  )}
                </Space>
              </Card>

              {showResult && result && (
                <Card
                  title={<span style={{ color: 'var(--text-primary)' }}>分析结果</span>}
                  style={cardStyle}
                  styles={{ header: cardHeaderStyle }}
                >
                  <AnalysisResultView result={result} />
                </Card>
              )}
            </Space>
          ) : (
            <Card
              style={{
                ...cardStyle,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: 400,
              }}
            >
              <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                <RocketOutlined style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }} />
                <div style={{ fontSize: 15 }}>提交分析任务后，这里将显示实时进度</div>
                <div style={{ fontSize: 13, marginTop: 8, opacity: 0.6 }}>
                  在左侧配置好分析参数后，点击「开始分析」
                </div>
              </div>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}
