import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import * as api from '@/lib/api';
import { getAccountTypeBadge, formatAccountType } from '@/lib/badges';
import { Plus, Search, Loader2, Building2 } from 'lucide-react';
import { toast } from 'sonner';

export default function AccountsList() {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [accounts, setAccounts] = useState<api.Account[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await api.getAccounts();
      setAccounts(data);
    } catch (error) {
      toast.error('Failed to load accounts');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = accounts
    .filter((a) => {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        a.name.toLowerCase().includes(query) ||
        (a.location || '').toLowerCase().includes(query);
      const matchesType = typeFilter === 'all' || a.account_type === typeFilter;
      return matchesSearch && matchesType;
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Accounts</h2>
            <p className="text-muted-foreground">Organizations & agency relationships</p>
          </div>
          <Button asChild>
            <Link to="/accounts/new">
              <Plus className="mr-2 h-4 w-4" />
              Add Account
            </Link>
          </Button>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search accounts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-full sm:w-52">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="government_agency">Government Agency</SelectItem>
              <SelectItem value="prime_contractor">Prime Contractor</SelectItem>
              <SelectItem value="subcontractor">Subcontractor</SelectItem>
              <SelectItem value="partner">Partner</SelectItem>
              <SelectItem value="vendor">Vendor</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length > 0 ? (
          <div className="space-y-4">
            {filtered.map((account) => (
              <Link key={account.id} to={`/accounts/${account.id}`}>
                <Card className="p-6 transition-shadow hover:shadow-md">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-3">
                      <Building2 className="h-5 w-5 mt-0.5 text-muted-foreground shrink-0" />
                      <div>
                        <h3 className="font-semibold">{account.name}</h3>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-sm text-muted-foreground">
                          {account.location && <span>{account.location}</span>}
                          {account.office && <span>{account.office}</span>}
                        </div>
                      </div>
                    </div>
                    <Badge variant={getAccountTypeBadge(account.account_type)} className="self-start">
                      {formatAccountType(account.account_type)}
                    </Badge>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card className="p-12 text-center">
            <p className="text-muted-foreground">
              {searchQuery || typeFilter !== 'all'
                ? 'No accounts found matching your filters.'
                : 'No accounts yet. Add your first organization.'}
            </p>
          </Card>
        )}
      </div>
    </Layout>
  );
}
