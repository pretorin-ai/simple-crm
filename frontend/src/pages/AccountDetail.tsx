import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import * as api from '@/lib/api';
import { getAccountTypeBadge, formatAccountType } from '@/lib/badges';
import { ArrowLeft, Trash2, Save, Loader2, Edit, X, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

const TYPES = ['government_agency', 'prime_contractor', 'subcontractor', 'partner', 'vendor'] as const;

const emptyAccount: api.Account = {
  id: '', name: '', account_type: 'government_agency', notes: '',
  created_at: '', updated_at: '',
};

export default function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [account, setAccount] = useState<api.Account | null>(null);
  const [editForm, setEditForm] = useState<api.Account | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const loadData = useCallback(async () => {
    try {
      if (id === 'new') {
        setAccount(emptyAccount);
        setEditForm({ ...emptyAccount });
        setIsEditing(true);
      } else if (id) {
        const data = await api.getAccount(id);
        setAccount(data);
      }
    } catch (error) {
      toast.error('Failed to load account');
      console.error(error);
      navigate('/accounts');
    } finally {
      setIsLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSave = async () => {
    if (!editForm) return;
    if (!editForm.name.trim()) { toast.error('Please enter a name'); return; }

    setIsSaving(true);
    try {
      const data: api.AccountCreate = {
        name: editForm.name,
        account_type: editForm.account_type,
        parent_agency: editForm.parent_agency || undefined,
        office: editForm.office || undefined,
        location: editForm.location || undefined,
        website: editForm.website || undefined,
        notes: editForm.notes,
      };

      if (id === 'new') {
        const created = await api.createAccount(data);
        toast.success('Account created');
        navigate(`/accounts/${created.id}`);
      } else {
        const updated = await api.updateAccount(editForm.id, data);
        setAccount(updated);
        setIsEditing(false);
        setEditForm(null);
        toast.success('Account updated');
      }
    } catch (error) {
      toast.error('Failed to save account');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!account) return;
    try {
      await api.deleteAccount(account.id);
      toast.success('Account deleted');
      navigate('/accounts');
    } catch (error) {
      toast.error('Failed to delete');
      console.error(error);
    }
  };

  if (isLoading) {
    return <Layout><div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div></Layout>;
  }

  if (!account && !isEditing) return null;
  const display = isEditing ? editForm : account;
  if (!display) return null;

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 sm:gap-4 min-w-0">
            <Button variant="outline" size="icon" asChild className="shrink-0">
              <Link to="/accounts"><ArrowLeft className="h-4 w-4" /></Link>
            </Button>
            <h2 className="text-xl sm:text-3xl font-bold tracking-tight truncate">
              {id === 'new' ? 'New Account' : display.name}
            </h2>
          </div>
          <div className="flex gap-2 self-end sm:self-auto">
            {isEditing ? (
              <>
                <Button size="sm" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</> : <><Save className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Save</span></>}
                </Button>
                {id !== 'new' && (
                  <Button variant="outline" size="sm" onClick={() => { setEditForm(null); setIsEditing(false); }}>
                    <X className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Cancel</span>
                  </Button>
                )}
              </>
            ) : (
              <>
                <Button size="sm" onClick={() => { setEditForm({ ...account! }); setIsEditing(true); }}>
                  <Edit className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Edit</span>
                </Button>
                <Button variant="destructive" size="sm" onClick={() => setShowDeleteConfirm(true)}>
                  <Trash2 className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Delete</span>
                </Button>
              </>
            )}
          </div>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Account Information</CardTitle>
              {!isEditing && (
                <Badge variant={getAccountTypeBadge(display.account_type)}>
                  {formatAccountType(display.account_type)}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEditing ? (
              <>
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input value={editForm!.name} onChange={(e) => setEditForm({ ...editForm!, name: e.target.value })} placeholder="Organization name" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Select value={editForm!.account_type} onValueChange={(v) => setEditForm({ ...editForm!, account_type: v as api.Account['account_type'] })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {TYPES.map((t) => <SelectItem key={t} value={t}>{formatAccountType(t)}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Parent Agency</Label>
                    <Input value={editForm!.parent_agency || ''} onChange={(e) => setEditForm({ ...editForm!, parent_agency: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Office</Label>
                    <Input value={editForm!.office || ''} onChange={(e) => setEditForm({ ...editForm!, office: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Location</Label>
                    <Input value={editForm!.location || ''} onChange={(e) => setEditForm({ ...editForm!, location: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Website</Label>
                  <Input type="url" value={editForm!.website || ''} onChange={(e) => setEditForm({ ...editForm!, website: e.target.value })} placeholder="https://..." />
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea value={editForm!.notes} onChange={(e) => setEditForm({ ...editForm!, notes: e.target.value })} rows={4} />
                </div>
              </>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <Label className="text-muted-foreground">Parent Agency</Label>
                    <p className="mt-1">{display.parent_agency || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Office</Label>
                    <p className="mt-1">{display.office || 'N/A'}</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <Label className="text-muted-foreground">Location</Label>
                    <p className="mt-1">{display.location || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Website</Label>
                    {display.website ? (
                      <a href={display.website} target="_blank" rel="noopener noreferrer" className="mt-1 flex items-center gap-1 text-primary hover:underline">
                        {display.website} <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <p className="mt-1">N/A</p>
                    )}
                  </div>
                </div>
                {display.notes && (
                  <div>
                    <Label className="text-muted-foreground">Notes</Label>
                    <p className="mt-1 whitespace-pre-wrap">{display.notes}</p>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        onConfirm={handleDelete}
        title="Delete Account"
        description="Are you sure you want to delete this account? This action cannot be undone."
        confirmLabel="Delete"
      />
    </Layout>
  );
}
