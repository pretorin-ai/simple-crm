import { useState, useEffect, useRef, DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import * as api from '@/lib/api';
import { getOpportunityStageBadge, formatCurrency } from '@/lib/badges';
import { Loader2, DollarSign, Target, TrendingUp, BarChart3 } from 'lucide-react';
import { toast } from 'sonner';

const STAGE_ORDER = ['identified', 'qualified', 'capture', 'teaming', 'proposal', 'submitted', 'awarded', 'lost'];

export default function Pipeline() {
  const [metrics, setMetrics] = useState<api.PipelineMetrics | null>(null);
  const [opportunities, setOpportunities] = useState<api.Opportunity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const draggedOppId = useRef<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [metricsData, oppsData] = await Promise.all([
        api.getPipelineMetrics(),
        api.getOpportunities(),
      ]);
      setMetrics(metricsData);
      setOpportunities(oppsData);
    } catch (error) {
      toast.error('Failed to load pipeline data');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDragStart = (e: DragEvent, oppId: string) => {
    draggedOppId.current = oppId;
    e.dataTransfer.effectAllowed = 'move';
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = '0.5';
    }
  };

  const handleDragEnd = (e: DragEvent) => {
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = '1';
    }
    draggedOppId.current = null;
    setDragOverStage(null);
  };

  const handleDragOver = (e: DragEvent, stage: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverStage(stage);
  };

  const handleDragLeave = (e: DragEvent, stage: string) => {
    const relatedTarget = e.relatedTarget as Node | null;
    if (e.currentTarget instanceof HTMLElement && !e.currentTarget.contains(relatedTarget)) {
      setDragOverStage((prev) => (prev === stage ? null : prev));
    }
  };

  const handleDrop = async (e: DragEvent, newStage: string) => {
    e.preventDefault();
    setDragOverStage(null);
    const oppId = draggedOppId.current;
    if (!oppId) return;

    const opp = opportunities.find((o) => o.id === oppId);
    if (!opp || opp.stage === newStage) return;

    const oldStage = opp.stage;
    // Optimistic update
    setOpportunities((prev) =>
      prev.map((o) => (o.id === oppId ? { ...o, stage: newStage as api.Opportunity['stage'] } : o))
    );

    try {
      await api.patchOpportunity(oppId, { stage: newStage });
      // Refresh metrics after stage change
      const metricsData = await api.getPipelineMetrics();
      setMetrics(metricsData);
      toast.success(`Moved "${opp.title}" to ${newStage}`);
    } catch (error) {
      // Revert on failure
      setOpportunities((prev) =>
        prev.map((o) => (o.id === oppId ? { ...o, stage: oldStage } : o))
      );
      toast.error('Failed to update opportunity stage');
      console.error(error);
    }
  };

  if (isLoading) {
    return <Layout><div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div></Layout>;
  }

  const oppsByStage: Record<string, api.Opportunity[]> = {};
  for (const opp of opportunities) {
    if (!oppsByStage[opp.stage]) oppsByStage[opp.stage] = [];
    oppsByStage[opp.stage].push(opp);
  }

  return (
    <Layout>
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Pipeline</h2>
          <p className="text-muted-foreground">Capture pipeline overview & forecasting</p>
        </div>

        {metrics && (
          <div className="grid gap-3 sm:gap-4 grid-cols-2 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pipeline Value</CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(metrics.pipeline_value)}</div>
                <p className="text-xs text-muted-foreground">{metrics.total_opportunities} opportunities</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Expected Revenue</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(metrics.expected_award_revenue)}</div>
                <p className="text-xs text-muted-foreground">Weighted by win probability</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics.win_rate}%</div>
                <p className="text-xs text-muted-foreground">Awarded / (Awarded + Lost)</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Deal Size</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(metrics.average_deal_size)}</div>
                <p className="text-xs text-muted-foreground">Across valued opportunities</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Pipeline Board */}
        <Card>
          <CardHeader>
            <CardTitle>Pipeline Board</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 overflow-x-auto pb-4 md:grid md:grid-cols-4 lg:grid-cols-8">
              {STAGE_ORDER.map((stage) => {
                const stageOpps = oppsByStage[stage] || [];
                const stageValue = stageOpps.reduce((sum, o) => sum + (o.estimated_value || 0), 0);
                const isOver = dragOverStage === stage;
                return (
                  <div
                    key={stage}
                    className={`space-y-2 rounded-lg p-2 transition-colors min-h-[120px] min-w-[140px] flex-shrink-0 md:min-w-0 ${isOver ? 'bg-accent/50 ring-2 ring-primary/30' : ''}`}
                    onDragOver={(e) => handleDragOver(e, stage)}
                    onDragLeave={(e) => handleDragLeave(e, stage)}
                    onDrop={(e) => handleDrop(e, stage)}
                  >
                    <div className="text-center">
                      <Badge variant={getOpportunityStageBadge(stage)} className="mb-1">
                        {stage}
                      </Badge>
                      <p className="text-xs text-muted-foreground">{stageOpps.length} opp{stageOpps.length !== 1 ? 's' : ''}</p>
                      <p className="text-xs font-medium">{formatCurrency(stageValue)}</p>
                    </div>
                    <div className="space-y-1">
                      {stageOpps.map((opp) => (
                        <Link
                          key={opp.id}
                          to={`/opportunities/${opp.id}`}
                          draggable
                          onDragStart={(e) => handleDragStart(e, opp.id)}
                          onDragEnd={handleDragEnd}
                        >
                          <div className="p-2 rounded border border-border hover:bg-accent/50 transition-colors text-xs cursor-grab active:cursor-grabbing">
                            <p className="font-medium truncate">{opp.title}</p>
                            <p className="text-muted-foreground">{formatCurrency(opp.estimated_value)}</p>
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* By Agency */}
        {metrics && Object.keys(metrics.by_agency).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>By Agency</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(metrics.by_agency)
                  .sort(([, a], [, b]) => b.value - a.value)
                  .map(([agency, data]) => (
                    <div key={agency} className="flex items-center justify-between p-3 rounded-lg border border-border">
                      <div>
                        <p className="font-medium">{agency}</p>
                        <p className="text-sm text-muted-foreground">{data.count} opportunit{data.count !== 1 ? 'ies' : 'y'}</p>
                      </div>
                      <p className="font-semibold">{formatCurrency(data.value)}</p>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}
