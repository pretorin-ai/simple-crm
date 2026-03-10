import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import * as api from '@/lib/api';
import { getOpportunityStageBadge, formatCurrency, formatSetAside } from '@/lib/badges';
import { Plus, Search, Loader2, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';

const STAGES = [
  { value: 'all', label: 'All Stages' },
  { value: 'identified', label: 'Identified' },
  { value: 'qualified', label: 'Qualified' },
  { value: 'capture', label: 'Capture' },
  { value: 'teaming', label: 'Teaming' },
  { value: 'proposal', label: 'Proposal' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'awarded', label: 'Awarded' },
  { value: 'lost', label: 'Lost' },
];

export default function OpportunitiesList() {
  const [searchQuery, setSearchQuery] = useState('');
  const [stageFilter, setStageFilter] = useState<string>('all');
  const [opportunities, setOpportunities] = useState<api.Opportunity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await api.getOpportunities();
      setOpportunities(data);
    } catch (error) {
      toast.error('Failed to load opportunities');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = opportunities
    .filter((opp) => {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        opp.title.toLowerCase().includes(query) ||
        (opp.agency || '').toLowerCase().includes(query) ||
        (opp.solicitation_number || '').toLowerCase().includes(query);
      const matchesStage = stageFilter === 'all' || opp.stage === stageFilter;
      return matchesSearch && matchesStage;
    })
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Opportunities</h2>
            <p className="text-muted-foreground">Capture pipeline & opportunity tracking</p>
          </div>
          <Button asChild>
            <Link to="/opportunities/new">
              <Plus className="mr-2 h-4 w-4" />
              Add Opportunity
            </Link>
          </Button>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search opportunities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={stageFilter} onValueChange={setStageFilter}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue placeholder="Stage" />
            </SelectTrigger>
            <SelectContent>
              {STAGES.map((s) => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length > 0 ? (
          <div className="space-y-4">
            {filtered.map((opp) => (
              <Link key={opp.id} to={`/opportunities/${opp.id}`}>
                <Card className="p-6 transition-shadow hover:shadow-md">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold">{opp.title}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {opp.agency || 'No agency'} {opp.solicitation_number && `| ${opp.solicitation_number}`}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {opp.is_government_contract && (
                          <Badge variant="outline">Gov</Badge>
                        )}
                        <Badge variant={getOpportunityStageBadge(opp.stage)}>
                          {opp.stage}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 sm:gap-x-6 text-sm text-muted-foreground">
                      <span className="font-medium text-foreground">
                        {formatCurrency(opp.estimated_value)}
                      </span>
                      {opp.win_probability !== undefined && opp.win_probability !== null && (
                        <span className="flex items-center gap-1">
                          <TrendingUp className="h-3 w-3" />
                          {opp.win_probability}% win
                        </span>
                      )}
                      {opp.set_aside_type && (
                        <span>{formatSetAside(opp.set_aside_type)}</span>
                      )}
                      {opp.naics_code && <span>NAICS: {opp.naics_code}</span>}
                      {opp.proposal_due_date && (
                        <span>Due: {new Date(opp.proposal_due_date).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card className="p-12 text-center">
            <p className="text-muted-foreground">
              {searchQuery || stageFilter !== 'all'
                ? 'No opportunities found matching your filters.'
                : 'No opportunities yet. Start building your pipeline.'}
            </p>
          </Card>
        )}
      </div>
    </Layout>
  );
}
