import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import * as api from '@/lib/api';
import { getContactStatusBadge, getContactTypeBadge } from '@/lib/badges';
import { ImportGmailContactsDialog } from '@/components/ImportGmailContactsDialog';
import { Plus, Search, Mail, Phone, Loader2, Calendar, Download } from 'lucide-react';
import { toast } from 'sonner';

export default function ContactsList() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [contacts, setContacts] = useState<api.Contact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  useEffect(() => {
    loadContacts();
    api.getGmailStatus().then((s) => setGmailConnected(s.connected)).catch(() => {});
  }, []);

  const loadContacts = async () => {
    try {
      const data = await api.getContacts();
      setContacts(data);
    } catch (error) {
      toast.error('Failed to load contacts');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredContacts = useMemo(() =>
    contacts
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
        if (a.follow_up_date && b.follow_up_date) {
          return new Date(a.follow_up_date).getTime() - new Date(b.follow_up_date).getTime();
        }
        if (a.follow_up_date && !b.follow_up_date) {
          return -1;
        }
        if (!a.follow_up_date && b.follow_up_date) {
          return 1;
        }
        return a.last_name.localeCompare(b.last_name);
      }),
    [contacts, searchQuery, statusFilter]
  );

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Contacts</h2>
            <p className="text-muted-foreground">
              Manage your contact relationships
            </p>
          </div>
          <div className="flex gap-2">
            {gmailConnected && (
              <Button variant="outline" onClick={() => setImportDialogOpen(true)}>
                <Download className="mr-2 h-4 w-4" />
                <span className="hidden sm:inline">Import from Gmail</span>
                <span className="sm:hidden">Import</span>
              </Button>
            )}
            <Button asChild>
              <Link to="/contacts/new">
                <Plus className="mr-2 h-4 w-4" />
                <span className="hidden sm:inline">Add Contact</span>
                <span className="sm:hidden">Add</span>
              </Link>
            </Button>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search contacts..."
              aria-label="Search contacts"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-[180px]" aria-label="Filter by status">
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
                        {contact.email}
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
                        <Badge variant={getContactStatusBadge(contact.status)}>
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

      <ImportGmailContactsDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onImportComplete={loadContacts}
      />
    </Layout>
  );
}
