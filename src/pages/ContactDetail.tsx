import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import * as api from '@/lib/api';
import { ArrowLeft, Edit, Trash2, Plus, Mail, Phone, Building, Calendar, Loader2, User as UserIcon, Copy } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export default function ContactDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [contact, setContact] = useState<api.Contact | null>(null);
  const [communications, setCommunications] = useState<api.Communication[]>([]);
  const [users, setUsers] = useState<api.User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isCommDialogOpen, setIsCommDialogOpen] = useState(false);
  const [editForm, setEditForm] = useState<Partial<api.ContactCreate>>({});
  const [commForm, setCommForm] = useState({
    type: 'email' as api.CommunicationCreate['type'],
    date: new Date().toISOString(),
    notes: '',
  });

  useEffect(() => {
    loadUsers();
    if (id === 'new') {
      setContact({
        id: 'new',
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        organization: '',
        contact_type: 'individual',
        status: 'cold',
        needs_follow_up: false,
        follow_up_date: undefined,
        notes: '',
        created_at: new Date().toISOString(),
        assigned_user_id: currentUser?.id || '',
      });
      setEditForm({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        organization: '',
        contact_type: 'individual',
        status: 'cold',
        needs_follow_up: false,
        follow_up_date: undefined,
        notes: '',
        assigned_user_id: currentUser?.id,
      });
      setIsEditDialogOpen(true);
      setIsLoading(false);
    } else if (id) {
      loadContact(id);
    }
  }, [id, currentUser]);

  const loadUsers = async () => {
    try {
      const usersData = await api.getUsers();
      setUsers(usersData);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadContact = async (contactId: string) => {
    try {
      const [contactData, commData] = await Promise.all([
        api.getContact(contactId),
        api.getCommunications(contactId)
      ]);
      setContact(contactData);
      setCommunications(commData);
    } catch (error) {
      toast.error('Failed to load contact');
      navigate('/contacts');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editForm.first_name || !editForm.last_name || !editForm.email) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      if (id === 'new') {
        const created = await api.createContact(editForm as api.ContactCreate);
        setIsEditDialogOpen(false);
        toast.success('Contact created successfully');
        navigate(`/contacts/${created.id}`);
      } else if (contact) {
        const updated = await api.updateContact(contact.id, editForm as api.ContactCreate);
        setContact(updated);
        setIsEditDialogOpen(false);
        toast.success('Contact saved successfully');
      }
    } catch (error) {
      toast.error('Failed to save contact');
    }
  };

  const handleDelete = async () => {
    if (contact && confirm('Are you sure you want to delete this contact?')) {
      try {
        await api.deleteContact(contact.id);
        toast.success('Contact deleted successfully');
        navigate('/contacts', { replace: true });
      } catch (error) {
        toast.error('Failed to delete contact');
      }
    }
  };

  const handleAddCommunication = async () => {
    if (!contact || !commForm.notes) {
      toast.error('Please add notes');
      return;
    }

    try {
      const newComm = await api.createCommunication({
        contact_id: contact.id,
        ...commForm,
      });
      setCommunications([newComm, ...communications]);
      setCommForm({
        type: 'email',
        date: new Date().toISOString(),
        notes: '',
      });
      setIsCommDialogOpen(false);
      toast.success('Communication logged successfully');

      // Reload contact to get updated last_contacted_at
      if (id && id !== 'new') {
        loadContact(id);
      }
    } catch (error) {
      toast.error('Failed to log communication');
    }
  };

  const handleQuickStatusUpdate = async (status: api.Contact['status']) => {
    if (!contact) return;
    try {
      const updated = await api.updateContact(contact.id, {
        first_name: contact.first_name,
        last_name: contact.last_name,
        email: contact.email,
        phone: contact.phone,
        organization: contact.organization,
        contact_type: contact.contact_type,
        status,
        needs_follow_up: contact.needs_follow_up,
        follow_up_date: contact.follow_up_date,
        notes: contact.notes,
      });
      setContact(updated);
      toast.success(`Status updated to ${status}`);
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleUpdateFollowUp = async (needsFollowUp: boolean, followUpDate?: string) => {
    if (!contact) return;
    try {
      const updated = await api.updateContact(contact.id, {
        first_name: contact.first_name,
        last_name: contact.last_name,
        email: contact.email,
        phone: contact.phone,
        organization: contact.organization,
        contact_type: contact.contact_type,
        status: contact.status,
        needs_follow_up: needsFollowUp,
        follow_up_date: followUpDate,
        notes: contact.notes,
        assigned_user_id: contact.assigned_user_id,
      });
      setContact(updated);
      toast.success('Follow-up updated successfully');
    } catch (error) {
      console.error('Follow-up update error:', error);
      toast.error('Failed to update follow-up');
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </Layout>
    );
  }

  if (!contact) return null;

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="outline" size="icon" asChild>
              <Link to="/contacts">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div>
              <h2 className="text-3xl font-bold tracking-tight">
                {contact.first_name} {contact.last_name}
              </h2>
              <p className="text-muted-foreground">{contact.organization}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setEditForm({
                  first_name: contact.first_name,
                  last_name: contact.last_name,
                  email: contact.email,
                  phone: contact.phone,
                  organization: contact.organization,
                  contact_type: contact.contact_type,
                  status: contact.status,
                  needs_follow_up: contact.needs_follow_up,
                  follow_up_date: contact.follow_up_date,
                  notes: contact.notes,
                  assigned_user_id: contact.assigned_user_id,
                });
                setIsEditDialogOpen(true);
              }}
            >
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        </div>

        {/* Follow-up Panel */}
        <Card>
          <CardHeader>
            <CardTitle>Follow-up</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <Label htmlFor="needs-follow-up">Needs Follow-up</Label>
                <p className="text-xs text-muted-foreground mt-1">Flag this contact for follow-up</p>
              </div>
              <Switch
                id="needs-follow-up"
                checked={contact.needs_follow_up}
                onCheckedChange={(checked) => {
                  handleUpdateFollowUp(checked, checked ? contact.follow_up_date : undefined);
                }}
              />
            </div>
            {contact.needs_follow_up && (
              <div className="mt-4 space-y-2">
                <Label htmlFor="follow-up-date">Follow-up Date</Label>
                <Input
                  id="follow-up-date"
                  type="date"
                  value={contact.follow_up_date ? new Date(contact.follow_up_date).toISOString().split('T')[0] : ''}
                  onChange={(e) => {
                    const value = e.target.value ? new Date(e.target.value).toISOString() : undefined;
                    handleUpdateFollowUp(contact.needs_follow_up, value);
                  }}
                />
                <p className="text-xs text-muted-foreground">
                  Set a specific date to follow up with this contact
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Email</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm text-muted-foreground">{contact.email}</p>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(contact.email);
                        toast.success('Email copied!');
                      }}
                      className="p-1 hover:bg-muted rounded transition-colors"
                      title="Copy email"
                    >
                      <Copy className="h-3 w-3 text-muted-foreground" />
                    </button>
                  </div>
                </div>
              </div>
              {contact.phone && (
                <div className="flex items-center gap-3">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Phone</p>
                    <p className="text-sm text-muted-foreground">{contact.phone}</p>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-3">
                <Building className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Organization</p>
                  <p className="text-sm text-muted-foreground">{contact.organization}</p>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium">Type</p>
                <Badge className="mt-1">{contact.contact_type}</Badge>
              </div>
              <div>
                <p className="text-sm font-medium">Status</p>
                <div className="mt-1 flex gap-2">
                  {(['cold', 'warm', 'hot'] as const).map((status) => (
                    <Badge
                      key={status}
                      variant={contact.status === status ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => handleQuickStatusUpdate(status)}
                    >
                      {status}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <UserIcon className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Assigned To</p>
                  <p className="text-sm text-muted-foreground">
                    {contact.assigned_user?.name || 'Loading...'}
                  </p>
                </div>
              </div>
              {contact.notes && (
                <div>
                  <p className="text-sm font-medium">Notes</p>
                  <p className="mt-1 text-sm text-muted-foreground">{contact.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Communications</CardTitle>
              <Button size="sm" onClick={() => setIsCommDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Log
              </Button>
            </CardHeader>
            <CardContent>
              {communications.length > 0 ? (
                <div className="space-y-4">
                  {communications.map((comm) => (
                    <div key={comm.id} className="border-b border-border pb-4 last:border-0">
                      <div className="flex items-start justify-between">
                        <div>
                          <Badge variant="outline">{comm.type}</Badge>
                          <p className="mt-2 text-sm">{comm.notes}</p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(comm.date).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No communications logged yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{id === 'new' ? 'Add Contact' : 'Edit Contact'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>First Name *</Label>
                <Input
                  value={editForm.first_name || ''}
                  onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Last Name *</Label>
                <Input
                  value={editForm.last_name || ''}
                  onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Email *</Label>
              <Input
                type="email"
                value={editForm.email || ''}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input
                value={editForm.phone || ''}
                onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Organization</Label>
              <Input
                value={editForm.organization || ''}
                onChange={(e) => setEditForm({ ...editForm, organization: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Contact Type</Label>
              <Select
                value={editForm.contact_type}
                onValueChange={(value) => setEditForm({ ...editForm, contact_type: value as api.Contact['contact_type'] })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="individual">Individual</SelectItem>
                  <SelectItem value="commercial">Commercial</SelectItem>
                  <SelectItem value="government">Government</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={editForm.status}
                onValueChange={(value) => setEditForm({ ...editForm, status: value as api.Contact['status'] })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cold">Cold</SelectItem>
                  <SelectItem value="warm">Warm</SelectItem>
                  <SelectItem value="hot">Hot</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Assigned To</Label>
              <Select
                value={editForm.assigned_user_id}
                onValueChange={(value) => setEditForm({ ...editForm, assigned_user_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a user" />
                </SelectTrigger>
                <SelectContent>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.name} ({user.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Assign this contact to a team member
              </p>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes || ''}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Communication Dialog */}
      <Dialog open={isCommDialogOpen} onOpenChange={setIsCommDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Log Communication</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={commForm.type}
                onValueChange={(value) => setCommForm({ ...commForm, type: value as api.CommunicationCreate['type'] })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="phone">Phone Call</SelectItem>
                  <SelectItem value="meeting">Meeting</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Date</Label>
              <Input
                type="date"
                value={new Date(commForm.date).toISOString().split('T')[0]}
                onChange={(e) => setCommForm({ ...commForm, date: new Date(e.target.value).toISOString() })}
              />
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={commForm.notes}
                onChange={(e) => setCommForm({ ...commForm, notes: e.target.value })}
                rows={4}
                placeholder="What was discussed?"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCommDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddCommunication}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
