import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import * as api from '@/lib/api';
import { Plus, Search, Mail, Phone, Loader2, Calendar, Copy, UserCheck, UserX, ArrowLeftRight } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export default function ContactsList() {
  const { refreshQueueCounts } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [contacts, setContacts] = useState<api.Contact[]>([]);
  const [pendingContacts, setPendingContacts] = useState<api.Contact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    loadContacts();
  }, []);

  const loadContacts = async () => {
    try {
      const [contactsData, pendingData] = await Promise.all([
        api.getContacts(),
        api.getPendingAcceptanceContacts(),
      ]);
      setContacts(contactsData);
      setPendingContacts(pendingData);
    } catch (error) {
      toast.error('Failed to load contacts');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcceptContact = async (contactId: string) => {
    setProcessingId(contactId);
    try {
      await api.acceptContactReassignment(contactId);
      toast.success('Contact accepted');
      setPendingContacts(prev => prev.filter(c => c.id !== contactId));
      // Reload contacts to get the newly accepted contact
      const updatedContacts = await api.getContacts();
      setContacts(updatedContacts);
      refreshQueueCounts();
    } catch (error) {
      toast.error('Failed to accept contact');
      console.error(error);
    } finally {
      setProcessingId(null);
    }
  };

  const handleRejectContact = async (contactId: string) => {
    setProcessingId(contactId);
    try {
      await api.rejectContactReassignment(contactId);
      toast.success('Contact returned to previous owner');
      setPendingContacts(prev => prev.filter(c => c.id !== contactId));
      refreshQueueCounts();
    } catch (error) {
      toast.error('Failed to reject contact');
      console.error(error);
    } finally {
      setProcessingId(null);
    }
  };

  const filteredContacts = contacts
    .filter((contact) => {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        contact.first_name.toLowerCase().includes(query) ||
        contact.last_name.toLowerCase().includes(query) ||
        contact.email.toLowerCase().includes(query) ||
        contact.organization.toLowerCase().includes(query);

      const matchesStatus = statusFilter === 'all' || contact.status === statusFilter;

      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      // Sort by follow_up_date (soonest first)
      // Contacts with follow_up_date come first, then by date
      // Contacts without follow_up_date come last
      if (a.follow_up_date && b.follow_up_date) {
        return new Date(a.follow_up_date).getTime() - new Date(b.follow_up_date).getTime();
      }
      if (a.follow_up_date && !b.follow_up_date) {
        return -1; // a comes first
      }
      if (!a.follow_up_date && b.follow_up_date) {
        return 1; // b comes first
      }
      // Both have no follow_up_date, sort by last name
      return a.last_name.localeCompare(b.last_name);
    });

  const getContactTypeBadge = (type: string) => {
    const variants = {
      individual: 'default',
      government: 'secondary',
      commercial: 'outline',
    } as const;
    return variants[type as keyof typeof variants] || 'outline';
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      cold: 'secondary',
      warm: 'default',
      hot: 'destructive',
    } as const;
    return variants[status as keyof typeof variants] || 'outline';
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Contacts</h2>
            <p className="text-muted-foreground">
              Manage your contact relationships
            </p>
          </div>
          <Button asChild>
            <Link to="/contacts/new">
              <Plus className="mr-2 h-4 w-4" />
              Add Contact
            </Link>
          </Button>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search contacts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="hot">Hot</SelectItem>
              <SelectItem value="warm">Warm</SelectItem>
              <SelectItem value="cold">Cold</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Pending Assignments Section */}
        {pendingContacts.length > 0 && (
          <Card className="p-6 border-2 border-primary/50 bg-primary/5">
            <div className="flex items-center gap-2 mb-4">
              <ArrowLeftRight className="h-5 w-5 text-primary" />
              <h3 className="text-lg font-semibold">Pending Assignments</h3>
              <Badge variant="default">{pendingContacts.length}</Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              These contacts have been reassigned to you and require your acceptance.
            </p>
            <div className="space-y-3">
              {pendingContacts.map((contact) => (
                <div
                  key={contact.id}
                  className="flex items-center justify-between p-4 rounded-lg border border-border bg-background"
                >
                  <div>
                    <p className="font-medium">
                      {contact.first_name} {contact.last_name}
                    </p>
                    <p className="text-sm text-muted-foreground">{contact.organization}</p>
                    <p className="text-xs text-muted-foreground">{contact.email}</p>
                    {contact.reassigned_by_user && (
                      <p className="text-xs text-primary mt-1">
                        Reassigned by: {contact.reassigned_by_user.name}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleRejectContact(contact.id)}
                      disabled={processingId === contact.id}
                    >
                      {processingId === contact.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <UserX className="h-4 w-4 mr-1" />
                          Reject
                        </>
                      )}
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleAcceptContact(contact.id)}
                      disabled={processingId === contact.id}
                    >
                      {processingId === contact.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <UserCheck className="h-4 w-4 mr-1" />
                          Accept
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Contacts Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredContacts.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredContacts.map((contact) => (
              <Link key={contact.id} to={`/contacts/${contact.id}`}>
                <Card className="p-6 transition-shadow hover:shadow-md">
                  <div className="space-y-3">
                    <div>
                      <h3 className="font-semibold">
                        {contact.first_name} {contact.last_name}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {contact.organization}
                      </p>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Mail className="h-3 w-3" />
                        <span className="truncate">{contact.email}</span>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            navigator.clipboard.writeText(contact.email);
                            toast.success('Email copied!');
                          }}
                          className="p-1 hover:bg-muted rounded transition-colors"
                          title="Copy email"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                      {contact.phone && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Phone className="h-3 w-3" />
                          {contact.phone}
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <Badge variant={getContactTypeBadge(contact.contact_type)}>
                          {contact.contact_type}
                        </Badge>
                        <Badge variant={getStatusBadge(contact.status)}>
                          {contact.status}
                        </Badge>
                      </div>
                      {contact.follow_up_date && (
                        <div className="flex items-center gap-1 text-xs text-primary font-medium">
                          <Calendar className="h-3 w-3" />
                          Follow up: {new Date(contact.follow_up_date).toLocaleDateString()}
                        </div>
                      )}
                      {contact.last_contacted_at && (
                        <span className="text-xs text-muted-foreground">
                          Last: {new Date(contact.last_contacted_at).toLocaleDateString()}
                        </span>
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
              {searchQuery
                ? 'No contacts found matching your search.'
                : 'No contacts yet. Add your first contact to get started.'}
            </p>
          </Card>
        )}
      </div>
    </Layout>
  );
}
