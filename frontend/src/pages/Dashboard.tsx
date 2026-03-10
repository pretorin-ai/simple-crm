import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import * as api from '@/lib/api';
import { getOpportunityStageBadge, formatCurrency, getComplianceStatusBadge, formatCertificationType } from '@/lib/badges';
import { AlertCircle, Calendar, Loader2, Clock, Target, DollarSign, TrendingUp, ShieldAlert } from 'lucide-react';
import { toast } from 'sonner';

export default function Dashboard() {
  const navigate = useNavigate();
  const [dueFollowUps, setDueFollowUps] = useState<api.Contact[]>([]);
  const [overdueFollowUps, setOverdueFollowUps] = useState<api.Contact[]>([]);
  const [pipelineMetrics, setPipelineMetrics] = useState<api.PipelineMetrics | null>(null);
  const [expiring, setExpiring] = useState<api.ComplianceRecord[]>([]);
  const [opportunities, setOpportunities] = useState<api.Opportunity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dueData, overdueData, metricsData, expiringData, oppsData] = await Promise.all([
        api.getDueFollowUps(7),
        api.getOverdueFollowUps(),
        api.getPipelineMetrics().catch(() => null),
        api.getExpiringCertifications(90).catch(() => []),
        api.getOpportunities().catch(() => []),
      ]);
      setDueFollowUps(dueData);
      setOverdueFollowUps(overdueData);
      setPipelineMetrics(metricsData);
      setExpiring(expiringData);
      setOpportunities(oppsData);
    } catch (error) {
      toast.error('Failed to load dashboard data');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const stats = useMemo(() => {
    // Active opportunities (not awarded/lost)
    const activeOpps = opportunities.filter((o) => o.stage !== 'awarded' && o.stage !== 'lost');

    return {
      totalFollowUps: overdueFollowUps.length + dueFollowUps.length,
      overdueCount: overdueFollowUps.length,
      dueCount: dueFollowUps.length,
      activeOpps,
    };
  }, [dueFollowUps, overdueFollowUps, opportunities]);

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Simple CRM overview
          </p>
        </div>

        {/* Pipeline Stats */}
        <div className="grid gap-3 sm:gap-4 grid-cols-2 md:grid-cols-4">
          {pipelineMetrics && (
            <>
              <Card className="cursor-pointer transition-colors hover:bg-accent/50" onClick={() => navigate('/pipeline')}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Pipeline Value</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(pipelineMetrics.pipeline_value)}</div>
                  <p className="text-xs text-muted-foreground">{pipelineMetrics.total_opportunities} total opportunities</p>
                </CardContent>
              </Card>
              <Card className="cursor-pointer transition-colors hover:bg-accent/50" onClick={() => navigate('/pipeline')}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Expected Revenue</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(pipelineMetrics.expected_award_revenue)}</div>
                  <p className="text-xs text-muted-foreground">Win probability weighted</p>
                </CardContent>
              </Card>
            </>
          )}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Follow-ups</CardTitle>
              <AlertCircle className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalFollowUps}</div>
              <p className="text-xs text-muted-foreground">
                {stats.overdueCount > 0 && (
                  <span className="text-destructive font-medium">{stats.overdueCount} overdue</span>
                )}
                {stats.overdueCount > 0 && stats.dueCount > 0 && ', '}
                {stats.dueCount > 0 && <span>{stats.dueCount} due soon</span>}
                {stats.totalFollowUps === 0 && 'No follow-ups'}
              </p>
            </CardContent>
          </Card>
          <Card className="cursor-pointer transition-colors hover:bg-accent/50" onClick={() => navigate('/opportunities')}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Opportunities</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.activeOpps.length}</div>
              <p className="text-xs text-muted-foreground">In pipeline</p>
            </CardContent>
          </Card>
        </div>

        {/* Expiring Certifications Alert */}
        {expiring.length > 0 && (
          <Card className="border-yellow-500/50 bg-yellow-500/5">
            <CardHeader>
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-yellow-600" />
                <CardTitle className="text-yellow-700">Certifications Expiring Soon</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {expiring.map((r) => (
                  <Link key={r.id} to="/compliance" className="flex items-center justify-between p-3 rounded-lg border border-yellow-500/30 hover:bg-yellow-500/10 transition-colors">
                    <div>
                      <p className="font-medium">{formatCertificationType(r.certification_type)}</p>
                      <p className="text-sm text-muted-foreground">
                        Expires: {r.expiration_date ? new Date(r.expiration_date).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                    <Badge variant={getComplianceStatusBadge(r.status)}>{r.status.replace(/_/g, ' ')}</Badge>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* To Do Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>To Do</CardTitle>
              <AlertCircle className="h-5 w-5 text-primary" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Overdue Follow-ups */}
              {overdueFollowUps.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle className="h-4 w-4 text-destructive" />
                    <h4 className="font-medium text-destructive">Overdue Follow-ups</h4>
                    <Badge variant="destructive">{overdueFollowUps.length}</Badge>
                  </div>
                  <div className="space-y-2">
                    {overdueFollowUps.map((contact) => (
                      <Link key={contact.id} to={`/contacts/${contact.id}`}
                        className="flex items-center justify-between p-3 rounded-lg border-2 border-destructive/50 bg-destructive/5 hover:bg-destructive/10 transition-colors">
                        <div>
                          <p className="font-medium">{contact.first_name} {contact.last_name}</p>
                          <p className="text-sm text-muted-foreground">{contact.organization}</p>
                        </div>
                        <div className="text-right">
                          {contact.follow_up_date && (
                            <div className="flex items-center gap-1 text-xs text-destructive font-medium">
                              <Calendar className="h-3 w-3" />
                              Due: {new Date(contact.follow_up_date).toLocaleDateString()}
                            </div>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Due Follow-ups */}
              {dueFollowUps.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="h-4 w-4 text-primary" />
                    <h4 className="font-medium">Follow-ups Due Soon</h4>
                    <Badge variant="default">{dueFollowUps.length}</Badge>
                  </div>
                  <div className="space-y-2">
                    {dueFollowUps.map((contact) => (
                      <Link key={contact.id} to={`/contacts/${contact.id}`}
                        className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                        <div>
                          <p className="font-medium">{contact.first_name} {contact.last_name}</p>
                          <p className="text-sm text-muted-foreground">{contact.organization}</p>
                        </div>
                        <div className="text-right">
                          {contact.follow_up_date && (
                            <div className="flex items-center gap-1 text-xs text-primary font-medium">
                              <Calendar className="h-3 w-3" />
                              Due: {new Date(contact.follow_up_date).toLocaleDateString()}
                            </div>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Upcoming Opportunities */}
              {stats.activeOpps.filter((o) => o.proposal_due_date).length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Target className="h-4 w-4 text-primary" />
                    <h4 className="font-medium">Upcoming Opportunity Deadlines</h4>
                  </div>
                  <div className="space-y-2">
                    {stats.activeOpps
                      .filter((o) => o.proposal_due_date)
                      .sort((a, b) => new Date(a.proposal_due_date!).getTime() - new Date(b.proposal_due_date!).getTime())
                      .slice(0, 5)
                      .map((opp) => (
                        <Link key={opp.id} to={`/opportunities/${opp.id}`}
                          className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                          <div className="flex-1">
                            <p className="font-medium">{opp.title}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge variant={getOpportunityStageBadge(opp.stage)} className="text-xs">{opp.stage}</Badge>
                              <span className="text-sm text-muted-foreground">{formatCurrency(opp.estimated_value)}</span>
                            </div>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            Due: {new Date(opp.proposal_due_date!).toLocaleDateString()}
                          </span>
                        </Link>
                      ))}
                  </div>
                </div>
              )}

              {overdueFollowUps.length === 0 &&
               dueFollowUps.length === 0 &&
               stats.activeOpps.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No action items at the moment.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
