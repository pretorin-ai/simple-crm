import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import DOMPurify from 'dompurify';
import * as api from '@/lib/api';
import { ArrowLeft, Edit, Trash2, Plus, Mail, Phone, Building, Loader2, User as UserIcon, Send, Reply, Inbox, ArrowUpRight } from 'lucide-react';
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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [commForm, setCommForm] = useState({
    type: 'email' as api.CommunicationCreate['type'],
    date: new Date().toISOString(),
    notes: '',
  });
  const [gmailStatus, setGmailStatus] = useState<api.GmailStatus>({ connected: false });
  const [isEmailDialogOpen, setIsEmailDialogOpen] = useState(false);
  const [emailForm, setEmailForm] = useState({
    subject: '',
    body: '',
    reply_to_message_id: undefined as string | undefined,
    thread_id: undefined as string | undefined,
  });
  const [expandedEmailId, setExpandedEmailId] = useState<string | null>(null);

  const loadUsers = async () => {
    try {
      const usersData = await api.getUsers();
      setUsers(usersData);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadGmailStatus = async () => {
    try {
      const status = await api.getGmailStatus();
      setGmailStatus(status);
    } catch (error) {
      console.error('Failed to load Gmail status:', error);
    }
  };

  const loadContact = useCallback(async (contactId: string) => {
    try {
      const [contactData, commData] = await Promise.all([
        api.getContact(contactId),
        api.getCommunications(contactId)
      ]);
      setContact(contactData);
      setCommunications(commData);
    } catch (_error) {
      toast.error('Failed to load contact');
      navigate('/contacts');
    } finally {
      setIsLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    loadUsers();
    loadGmailStatus();
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
  }, [id, currentUser, loadContact]);

  const handleSave = async () => {
    if (!editForm.first_name || !editForm.last_name || !editForm.email) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      if (id === 'new') {
        const created = await api.createContact(editForm as api.ContactCreate);
        toast.success('Contact created successfully');
        navigate(`/contacts/${created.id}`);
      } else if (contact) {
        const updated = await api.updateContact(contact.id, editForm as api.ContactCreate);
        setContact(updated);
        setIsEditDialogOpen(false);
        toast.success('Contact saved successfully');
      }
    } catch (_error) {
      toast.error('Failed to save contact');
    }
  };

  const handleDelete = async () => {
    if (!contact) return;
    try {
      await api.deleteContact(contact.id);
      toast.success('Contact deleted successfully');
      navigate('/contacts');
    } catch (_error) {
      toast.error('Failed to delete contact');
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
    } catch (_error) {
      toast.error('Failed to log communication');
    }
  };

  const handleQuickStatusUpdate = async (status: api.Contact['status']) => {
    if (!contact) return;
    try {
      const updated = await api.patchContact(contact.id, { status });
      setContact(updated);
      toast.success(`Status updated to ${status}`);
    } catch (_error) {
      toast.error('Failed to update status');
    }
  };

  const handleUpdateFollowUp = async (needsFollowUp: boolean, followUpDate?: string) => {
    if (!contact) return;
    try {
      const updated = await api.patchContact(contact.id, {
        needs_follow_up: needsFollowUp,
        follow_up_date: followUpDate,
      });
      setContact(updated);
      toast.success('Follow-up updated successfully');
    } catch (error) {
      console.error('Follow-up update error:', error);
      toast.error('Failed to update follow-up');
    }
  };

  const handleSendEmail = async () => {
    if (!contact || !emailForm.subject || !emailForm.body) {
      toast.error('Please fill in subject and body');
      return;
    }
    try {
      const newComm = await api.sendGmailEmail({
        to: contact.email,
        subject: emailForm.subject,
        body: emailForm.body,
        contact_id: contact.id,
        reply_to_message_id: emailForm.reply_to_message_id,
        thread_id: emailForm.thread_id,
      });
      setCommunications([newComm, ...communications]);
      setEmailForm({ subject: '', body: '', reply_to_message_id: undefined, thread_id: undefined });
      setIsEmailDialogOpen(false);
      toast.success('Email sent successfully');
      if (id && id !== 'new') loadContact(id);
    } catch (_error) {
      toast.error('Failed to send email');
    }
  };

  const handleReply = (comm: api.Communication) => {
    setEmailForm({
      subject: comm.subject?.startsWith('Re: ') ? comm.subject : `Re: ${comm.subject || ''}`,
      body: '',
      reply_to_message_id: comm.gmail_message_id,
      thread_id: comm.gmail_thread_id,
    });
    setIsEmailDialogOpen(true);
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
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 sm:gap-4">
            <Button variant="outline" size="icon" asChild>
              <Link to="/contacts">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div className="min-w-0">
              <h2 className="text-xl sm:text-3xl font-bold tracking-tight truncate">
                {contact.first_name} {contact.last_name}
              </h2>
              <p className="text-muted-foreground text-sm sm:text-base">{contact.organization}</p>
            </div>
          </div>
          <div className="flex gap-2 self-end sm:self-auto">
            <Button
              variant="outline"
              size="sm"
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
              <Edit className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Edit</span>
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setShowDeleteConfirm(true)}>
              <Trash2 className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Delete</span>
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
                <div>
                  <p className="text-sm font-medium">Email</p>
                  <p className="text-sm text-muted-foreground">{contact.email}</p>
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
              <div className="flex gap-2">
                {gmailStatus.connected && id !== 'new' && (
                  <Button size="sm" variant="outline" onClick={() => {
                    setEmailForm({ subject: '', body: '', reply_to_message_id: undefined, thread_id: undefined });
                    setIsEmailDialogOpen(true);
                  }}>
                    <Send className="mr-2 h-4 w-4" />
                    Email
                  </Button>
                )}
                <Button size="sm" onClick={() => setIsCommDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Log
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {communications.length > 0 ? (
                <div className="space-y-4">
                  {communications.map((comm) => (
                    <div key={comm.id} className="border-b border-border pb-4 last:border-0">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">{comm.type}</Badge>
                            {comm.direction === 'inbound' && (
                              <Badge variant="secondary" className="text-xs">
                                <Inbox className="mr-1 h-3 w-3" />
                                Received
                              </Badge>
                            )}
                            {comm.direction === 'outbound' && (
                              <Badge variant="secondary" className="text-xs">
                                <ArrowUpRight className="mr-1 h-3 w-3" />
                                Sent
                              </Badge>
                            )}
                          </div>
                          {comm.subject && (
                            <p className="mt-1 text-sm font-medium">{comm.subject}</p>
                          )}
                          {comm.gmail_message_id ? (
                            <div className="mt-1">
                              {comm.email_from && (
                                <p className="text-xs text-muted-foreground truncate">
                                  From: {comm.email_from}
                                </p>
                              )}
                              <button
                                onClick={() => setExpandedEmailId(expandedEmailId === comm.id ? null : comm.id)}
                                className="text-xs text-blue-600 hover:text-blue-800 mt-1"
                              >
                                {expandedEmailId === comm.id ? 'Hide' : 'Show'} content
                              </button>
                              {expandedEmailId === comm.id && (
                                <div className="mt-2 rounded border p-3 bg-muted/30">
                                  {comm.body_html ? (
                                    <div
                                      className="text-sm prose prose-sm max-w-none"
                                      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comm.body_html) }}
                                    />
                                  ) : (
                                    <p className="text-sm whitespace-pre-wrap">{comm.notes}</p>
                                  )}
                                </div>
                              )}
                              {gmailStatus.connected && comm.direction === 'inbound' && (
                                <button
                                  onClick={() => handleReply(comm)}
                                  className="inline-flex items-center text-xs text-blue-600 hover:text-blue-800 mt-1 ml-2"
                                >
                                  <Reply className="mr-1 h-3 w-3" />
                                  Reply
                                </button>
                              )}
                            </div>
                          ) : (
                            <p className="mt-2 text-sm">{comm.notes}</p>
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground ml-2 shrink-0">
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

      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        onConfirm={handleDelete}
        title="Delete Contact"
        description="Are you sure you want to delete this contact? This action cannot be undone and will also remove all associated communications."
        confirmLabel="Delete"
      />

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

      {/* Email Compose Dialog */}
      <Dialog open={isEmailDialogOpen} onOpenChange={setIsEmailDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {emailForm.reply_to_message_id ? 'Reply to Email' : 'Compose Email'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>To</Label>
              <Input value={contact?.email || ''} disabled />
            </div>
            <div className="space-y-2">
              <Label>Subject</Label>
              <Input
                value={emailForm.subject}
                onChange={(e) => setEmailForm({ ...emailForm, subject: e.target.value })}
                placeholder="Email subject"
              />
            </div>
            <div className="space-y-2">
              <Label>Body</Label>
              <Textarea
                value={emailForm.body}
                onChange={(e) => setEmailForm({ ...emailForm, body: e.target.value })}
                rows={8}
                placeholder="Write your email..."
              />
            </div>
            {gmailStatus.gmail_address && (
              <p className="text-xs text-muted-foreground">
                Sending from: {gmailStatus.gmail_address}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEmailDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSendEmail}>
              <Send className="mr-2 h-4 w-4" />
              Send
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
