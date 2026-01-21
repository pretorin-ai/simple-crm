import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import * as api from '@/lib/api';
import { FileText, AlertCircle, Calendar, Loader2, Clock, Inbox, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export default function Dashboard() {
  const { refreshQueueCounts } = useAuth();
  const [contacts, setContacts] = useState<api.Contact[]>([]);
  const [contracts, setContracts] = useState<api.Contract[]>([]);
  const [dueFollowUps, setDueFollowUps] = useState<api.Contact[]>([]);
  const [overdueFollowUps, setOverdueFollowUps] = useState<api.Contact[]>([]);
  const [unclaimedContacts, setUnclaimedContacts] = useState<api.Contact[]>([]);
  const [unclaimedContracts, setUnclaimedContracts] = useState<api.Contract[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [claimingId, setClaimingId] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [contactsData, contractsData, dueData, overdueData, unclaimedContactsData, unclaimedContractsData] = await Promise.all([
        api.getContacts(),
        api.getContracts(),
        api.getDueFollowUps(7), // Follow-ups due within 7 days
        api.getOverdueFollowUps(),
        api.getUnclaimedContacts(),
        api.getUnclaimedContracts(),
      ]);
      setContacts(contactsData);
      setContracts(contractsData);
      setDueFollowUps(dueData);
      setOverdueFollowUps(overdueData);
      setUnclaimedContacts(unclaimedContactsData);
      setUnclaimedContracts(unclaimedContractsData);
    } catch (error) {
      toast.error('Failed to load dashboard data');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClaimContact = async (contactId: string) => {
    setClaimingId(contactId);
    try {
      await api.claimContact(contactId);
      toast.success('Contact claimed successfully');
      setUnclaimedContacts(prev => prev.filter(c => c.id !== contactId));
      refreshQueueCounts();
    } catch (error) {
      toast.error('Failed to claim contact');
      console.error(error);
    } finally {
      setClaimingId(null);
    }
  };

  const handleClaimContract = async (contractId: string) => {
    setClaimingId(contractId);
    try {
      await api.claimContract(contractId);
      toast.success('Contract claimed successfully');
      setUnclaimedContracts(prev => prev.filter(c => c.id !== contractId));
      refreshQueueCounts();
    } catch (error) {
      toast.error('Failed to claim contract');
      console.error(error);
    } finally {
      setClaimingId(null);
    }
  };

  const stats = useMemo(() => {
    const prospectiveContracts = contracts.filter((c) => c.status === 'prospective');
    const inProgressContracts = contracts.filter((c) => c.status === 'in progress');
    const actionableContracts = [...prospectiveContracts, ...inProgressContracts]
      .sort((a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime());

    return {
      totalFollowUps: overdueFollowUps.length + dueFollowUps.length,
      overdueCount: overdueFollowUps.length,
      dueCount: dueFollowUps.length,
      prospectiveContracts: prospectiveContracts.length,
      inProgressContracts: inProgressContracts.length,
      actionableContracts,
    };
  }, [contacts, contracts, dueFollowUps, overdueFollowUps]);

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
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Overview of your CRM activity
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Follow-ups</CardTitle>
              <AlertCircle className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalFollowUps}</div>
              <p className="text-xs text-muted-foreground">
                {stats.overdueCount > 0 && (
                  <span className="text-destructive font-medium">
                    {stats.overdueCount} overdue
                  </span>
                )}
                {stats.overdueCount > 0 && stats.dueCount > 0 && ', '}
                {stats.dueCount > 0 && (
                  <span>
                    {stats.dueCount} due soon
                  </span>
                )}
                {stats.totalFollowUps === 0 && 'No follow-ups'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Prospective Contracts</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.prospectiveContracts}</div>
              <p className="text-xs text-muted-foreground">Opportunities being evaluated</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">In Progress Contracts</CardTitle>
              <FileText className="h-4 w-4 text-accent" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.inProgressContracts}</div>
              <p className="text-xs text-muted-foreground">Active submissions in progress</p>
            </CardContent>
          </Card>
        </div>

        {/* New Items to Claim Section */}
        {(unclaimedContacts.length > 0 || unclaimedContracts.length > 0) && (
          <Card className="border-2 border-primary/50 bg-primary/5">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Inbox className="h-5 w-5 text-primary" />
                  New Items to Claim
                </CardTitle>
                <Badge variant="default">
                  {unclaimedContacts.length + unclaimedContracts.length}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Unclaimed Contacts */}
                {unclaimedContacts.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <UserPlus className="h-4 w-4" />
                      New Contacts from API
                    </h4>
                    <div className="space-y-2">
                      {unclaimedContacts.map((contact) => (
                        <div
                          key={contact.id}
                          className="flex items-center justify-between p-3 rounded-lg border border-border bg-background"
                        >
                          <div>
                            <p className="font-medium">
                              {contact.first_name} {contact.last_name}
                            </p>
                            <p className="text-sm text-muted-foreground">{contact.organization}</p>
                            <p className="text-xs text-muted-foreground">{contact.email}</p>
                          </div>
                          <Button
                            size="sm"
                            onClick={() => handleClaimContact(contact.id)}
                            disabled={claimingId === contact.id}
                          >
                            {claimingId === contact.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              'Claim'
                            )}
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Unclaimed Contracts */}
                {unclaimedContracts.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2 flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      New Contracts from API
                    </h4>
                    <div className="space-y-2">
                      {unclaimedContracts.map((contract) => (
                        <div
                          key={contract.id}
                          className="flex items-center justify-between p-3 rounded-lg border border-border bg-background"
                        >
                          <div className="flex-1">
                            <p className="font-medium">{contract.title}</p>
                            <p className="text-sm text-muted-foreground">{contract.source}</p>
                            <p className="text-xs text-muted-foreground">
                              Deadline: {new Date(contract.deadline).toLocaleDateString()}
                            </p>
                          </div>
                          <Button
                            size="sm"
                            onClick={() => handleClaimContract(contract.id)}
                            disabled={claimingId === contract.id}
                          >
                            {claimingId === contract.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              'Claim'
                            )}
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
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
                      <Link
                        key={contact.id}
                        to={`/contacts/${contact.id}`}
                        className="flex items-center justify-between p-3 rounded-lg border-2 border-destructive/50 bg-destructive/5 hover:bg-destructive/10 transition-colors"
                      >
                        <div>
                          <p className="font-medium">
                            {contact.first_name} {contact.last_name}
                          </p>
                          <p className="text-sm text-muted-foreground">{contact.organization}</p>
                        </div>
                        <div className="text-right">
                          {contact.follow_up_date && (
                            <div className="flex items-center gap-1 text-xs text-destructive font-medium">
                              <Calendar className="h-3 w-3" />
                              Due: {new Date(contact.follow_up_date).toLocaleDateString()}
                            </div>
                          )}
                          {contact.last_contacted_at && (
                            <p className="text-xs text-muted-foreground">
                              Last contact: {new Date(contact.last_contacted_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Due Follow-ups (not overdue) */}
              {dueFollowUps.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="h-4 w-4 text-primary" />
                    <h4 className="font-medium">Follow-ups Due Soon</h4>
                    <Badge variant="default">{dueFollowUps.length}</Badge>
                  </div>
                  <div className="space-y-2">
                    {dueFollowUps.map((contact) => (
                      <Link
                        key={contact.id}
                        to={`/contacts/${contact.id}`}
                        className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                      >
                        <div>
                          <p className="font-medium">
                            {contact.first_name} {contact.last_name}
                          </p>
                          <p className="text-sm text-muted-foreground">{contact.organization}</p>
                        </div>
                        <div className="text-right">
                          {contact.follow_up_date && (
                            <div className="flex items-center gap-1 text-xs text-primary font-medium">
                              <Calendar className="h-3 w-3" />
                              Due: {new Date(contact.follow_up_date).toLocaleDateString()}
                            </div>
                          )}
                          {contact.last_contacted_at && (
                            <p className="text-xs text-muted-foreground">
                              Last contact: {new Date(contact.last_contacted_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Contracts to Action */}
              {stats.actionableContracts.length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Contracts to Action</h4>
                  <div className="space-y-2">
                    {stats.actionableContracts.slice(0, 5).map((contract) => (
                      <Link
                        key={contract.id}
                        to={`/contracts/${contract.id}`}
                        className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                      >
                        <div className="flex-1">
                          <p className="font-medium">{contract.title}</p>
                          <p className="text-sm text-muted-foreground capitalize">{contract.status}</p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          Deadline: {new Date(contract.deadline).toLocaleDateString()}
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {overdueFollowUps.length === 0 &&
               dueFollowUps.length === 0 &&
               stats.actionableContracts.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No action items at the moment. Great job! 🎉
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <div className="flex gap-4">
          <Button asChild>
            <Link to="/contacts/new">Add Contact</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/contracts/new">Add Contract</Link>
          </Button>
        </div>
      </div>
    </Layout>
  );
}
