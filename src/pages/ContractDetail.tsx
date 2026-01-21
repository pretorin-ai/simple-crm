import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import * as api from '@/lib/api';
import { ArrowLeft, Trash2, Save, ExternalLink, Loader2, Edit, X, Check, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [contract, setContract] = useState<api.Contract | null>(null);
  const [editForm, setEditForm] = useState<api.Contract | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      if (id === 'new') {
        const newContract = {
          id: '',
          title: '',
          description: '',
          source: '',
          deadline: new Date().toISOString().split('T')[0],
          status: 'prospective' as const,
          submission_link: '',
          assigned_contact_ids: [],
          notes: '',
          created_at: new Date().toISOString(),
        };
        setContract(newContract);
        setEditForm(newContract);
        setIsEditing(true);
      } else if (id) {
        const contractData = await api.getContract(id);
        setContract(contractData);
      }
    } catch (error) {
      toast.error('Failed to load contract');
      console.error(error);
      navigate('/contracts');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = () => {
    setEditForm({ ...contract! });
    setIsEditing(true);
  };

  const handleCancel = () => {
    setEditForm(null);
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!editForm) return;

    // Validation
    if (!editForm.title.trim()) {
      toast.error('Please enter a contract title');
      return;
    }
    if (!editForm.deadline) {
      toast.error('Please select a deadline');
      return;
    }

    setIsSaving(true);
    try {
      const contractData: api.ContractCreate = {
        title: editForm.title,
        description: editForm.description,
        source: editForm.source,
        deadline: editForm.deadline,
        status: editForm.status,
        submission_link: editForm.submission_link,
        notes: editForm.notes,
        assigned_contact_ids: editForm.assigned_contact_ids,
      };

      if (id === 'new') {
        const newContract = await api.createContract(contractData);
        toast.success('Contract created successfully');
        navigate(`/contracts/${newContract.id}`);
      } else {
        const updatedContract = await api.updateContract(editForm.id, contractData);
        setContract(updatedContract);
        setIsEditing(false);
        setEditForm(null);
        toast.success('Contract updated successfully');
      }
    } catch (error) {
      toast.error('Failed to save contract');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!contract || !confirm('Are you sure you want to delete this contract opportunity?')) {
      return;
    }

    try {
      await api.deleteContract(contract.id);
      toast.success('Contract deleted successfully');
      navigate('/contracts');
    } catch (error) {
      toast.error('Failed to delete contract');
      console.error(error);
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

  if (!contract && !isEditing) return null;

  const displayContract = isEditing ? editForm : contract;
  if (!displayContract) return null;

  const getStatusBadge = (status: string) => {
    const variants = {
      prospective: 'outline',
      'in progress': 'default',
      submitted: 'secondary',
      'not a good fit': 'destructive',
    } as const;
    return variants[status as keyof typeof variants] || 'outline';
  };

  const isDeadlineNear = () => {
    const deadlineDate = new Date(displayContract.deadline);
    const now = new Date();
    const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    return deadlineDate <= sevenDaysFromNow && deadlineDate >= now;
  };

  const renderDescriptionWithLinks = (text: string) => {
    if (!text) return 'No description';

    // Simple URL regex that matches http(s) URLs
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = text.split(urlRegex);

    return parts.map((part, index) => {
      if (part.match(urlRegex)) {
        return (
          <a
            key={index}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline inline-flex items-center gap-1"
          >
            {part}
            <ExternalLink className="h-3 w-3 inline" />
          </a>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="outline" size="icon" asChild>
              <Link to="/contracts">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div>
              <h2 className="text-3xl font-bold tracking-tight">
                {id === 'new' ? 'New Contract Opportunity' : displayContract.title}
              </h2>
            </div>
          </div>
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button onClick={handleSave} disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save
                    </>
                  )}
                </Button>
                {id !== 'new' && (
                  <Button variant="outline" onClick={handleCancel}>
                    <X className="mr-2 h-4 w-4" />
                    Cancel
                  </Button>
                )}
              </>
            ) : (
              <>
                <Button onClick={handleEdit}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Button>
                <Button variant="destructive" onClick={handleDelete}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Prominent Submission Link - Only show in view mode and if link exists */}
        {!isEditing && displayContract.submission_link && (
          <Card className="border-primary/50 bg-primary/5">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold mb-1">Draft Submission</h3>
                  <p className="text-sm text-muted-foreground">Click to open the draft submission document</p>
                </div>
                <Button size="lg" asChild>
                  <a href={displayContract.submission_link} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="mr-2 h-5 w-5" />
                    Open Draft
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Contract Information */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Contract Information</CardTitle>
              {!isEditing && (
                <Badge variant={getStatusBadge(displayContract.status)}>
                  {displayContract.status}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEditing ? (
              // Edit Mode
              <>
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input
                    value={editForm!.title}
                    onChange={(e) => setEditForm({ ...editForm!, title: e.target.value })}
                    placeholder="Contract title"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={editForm!.description}
                    onChange={(e) => setEditForm({ ...editForm!, description: e.target.value })}
                    rows={4}
                    placeholder="Contract description"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Source</Label>
                    <Input
                      value={editForm!.source}
                      onChange={(e) => setEditForm({ ...editForm!, source: e.target.value })}
                      placeholder="e.g., SAM.gov"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Deadline</Label>
                    <Input
                      type="date"
                      value={editForm!.deadline}
                      onChange={(e) => setEditForm({ ...editForm!, deadline: e.target.value })}
                    />
                    {isDeadlineNear() && (
                      <p className="text-xs text-primary">
                        ⚠️ Deadline is within 7 days
                      </p>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={editForm!.status}
                    onValueChange={(value) => setEditForm({ ...editForm!, status: value as api.Contract['status'] })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="prospective">Prospective</SelectItem>
                      <SelectItem value="in progress">In Progress</SelectItem>
                      <SelectItem value="submitted">Submitted</SelectItem>
                      <SelectItem value="not a good fit">Not a Good Fit</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Submission Link</Label>
                  <div className="flex gap-2">
                    <Input
                      type="url"
                      value={editForm!.submission_link || ''}
                      onChange={(e) => setEditForm({ ...editForm!, submission_link: e.target.value })}
                      placeholder="https://..."
                    />
                    {editForm!.submission_link && (
                      <Button
                        variant="outline"
                        size="icon"
                        asChild
                      >
                        <a href={editForm!.submission_link} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea
                    value={editForm!.notes}
                    onChange={(e) => setEditForm({ ...editForm!, notes: e.target.value })}
                    rows={4}
                    placeholder="Additional notes or requirements..."
                  />
                </div>
              </>
            ) : (
              // View Mode
              <>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <Label className="text-muted-foreground">Description</Label>
                    <p className="mt-1 break-words">{renderDescriptionWithLinks(displayContract.description)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Source</Label>
                    <p className="mt-1">{displayContract.source || 'Not specified'}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <Label className="text-muted-foreground">Deadline</Label>
                    <p className="mt-1 font-medium">
                      {new Date(displayContract.deadline).toLocaleDateString()}
                      {isDeadlineNear() && (
                        <span className="ml-2 text-xs text-primary">⚠️ Due within 7 days</span>
                      )}
                    </p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Created</Label>
                    <p className="mt-1">{new Date(displayContract.created_at).toLocaleDateString()}</p>
                  </div>
                </div>

                {displayContract.notes && (
                  <div>
                    <Label className="text-muted-foreground">Notes</Label>
                    <p className="mt-1 whitespace-pre-wrap">{displayContract.notes}</p>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
