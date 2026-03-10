import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import * as api from '@/lib/api';
import { getOpportunityStageBadge, formatCurrency, formatSetAside } from '@/lib/badges';
import { ArrowLeft, Trash2, Save, Loader2, Edit, X, Plus, Upload, Download, FileText, Clock, Users, Paperclip, BookOpen } from 'lucide-react';
import { toast } from 'sonner';

const STAGES = ['identified', 'qualified', 'capture', 'teaming', 'proposal', 'submitted', 'awarded', 'lost'] as const;
const SET_ASIDES = ['small_business', '8a', 'hubzone', 'wosb', 'sdvosb', 'full_and_open', 'none'] as const;
const SOURCES = ['sam_gov', 'agency_forecast', 'incumbent_recompete', 'partner_referral', 'internal'] as const;
const EVENT_TYPES = ['discovery', 'contact', 'rfp_release', 'proposal_submitted', 'meeting', 'stage_change', 'note', 'other'] as const;
const CAPTURE_SECTIONS = [
  { key: 'customer_intel', label: 'Customer Intel' },
  { key: 'incumbent', label: 'Incumbent' },
  { key: 'competitors', label: 'Competitors' },
  { key: 'partners', label: 'Partners' },
  { key: 'risks', label: 'Risks' },
  { key: 'strategy', label: 'Strategy' },
] as const;

const emptyOpp: api.Opportunity = {
  id: '', title: '', is_government_contract: false, description: '',
  agency: '', naics_code: '', stage: 'identified',
  notes: '', created_at: '', updated_at: '', vehicle_ids: [], vehicles: [],
  estimated_value: undefined, win_probability: undefined,
};

type Tab = 'timeline' | 'capture' | 'teaming' | 'attachments';

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [opp, setOpp] = useState<api.Opportunity | null>(null);
  const [editForm, setEditForm] = useState<api.Opportunity | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('timeline');

  // Timeline state
  const [timeline, setTimeline] = useState<api.OpportunityEvent[]>([]);
  const [showEventForm, setShowEventForm] = useState(false);
  const [newEvent, setNewEvent] = useState({ date: '', event_type: 'note' as api.OpportunityEvent['event_type'], description: '' });

  // Capture Notes state
  const [captureNotes, setCaptureNotes] = useState<Record<string, string>>({});
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [sectionDraft, setSectionDraft] = useState('');

  // Teaming state
  const [teamingRecords, setTeamingRecords] = useState<api.TeamingRecord[]>([]);

  // Attachments state
  const [attachments, setAttachments] = useState<api.AttachmentRecord[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isNew = id === 'new';

  const loadData = useCallback(async () => {
    try {
      if (isNew) {
        setOpp(emptyOpp);
        setEditForm({ ...emptyOpp });
        setIsEditing(true);
      } else if (id) {
        const data = await api.getOpportunity(id);
        setOpp(data);
      }
    } catch (error) {
      toast.error('Failed to load opportunity');
      console.error(error);
      navigate('/opportunities');
    } finally {
      setIsLoading(false);
    }
  }, [id, isNew, navigate]);

  const loadTabData = useCallback(async () => {
    if (isNew || !id) return;
    try {
      if (activeTab === 'timeline') {
        const data = await api.getTimeline(id);
        setTimeline(data);
      } else if (activeTab === 'capture') {
        const data = await api.getCaptureNotes(id);
        const map: Record<string, string> = {};
        for (const note of data) map[note.section] = note.content;
        setCaptureNotes(map);
      } else if (activeTab === 'teaming') {
        const data = await api.getTeamingRecords(id);
        setTeamingRecords(data);
      } else if (activeTab === 'attachments') {
        const data = await api.getAttachments(id);
        setAttachments(data);
      }
    } catch (error) {
      console.error('Failed to load tab data', error);
    }
  }, [id, isNew, activeTab]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { loadTabData(); }, [loadTabData]);

  const handleSave = async () => {
    if (!editForm) return;
    if (!editForm.title.trim()) { toast.error('Please enter a title'); return; }

    setIsSaving(true);
    try {
      const data: api.OpportunityCreate = {
        title: editForm.title,
        is_government_contract: editForm.is_government_contract,
        description: editForm.description,
        agency: editForm.agency || undefined,
        account_id: editForm.account_id || undefined,
        naics_code: editForm.naics_code || undefined,
        set_aside_type: editForm.set_aside_type || undefined,
        estimated_value: editForm.estimated_value || undefined,
        solicitation_number: editForm.solicitation_number || undefined,
        sam_gov_notice_id: editForm.sam_gov_notice_id || undefined,
        submission_link: editForm.submission_link || undefined,
        deadline: editForm.deadline || undefined,
        source: editForm.source || undefined,
        stage: editForm.stage,
        capture_manager_id: editForm.capture_manager_id || undefined,
        expected_release_date: editForm.expected_release_date || undefined,
        proposal_due_date: editForm.proposal_due_date || undefined,
        award_date_estimate: editForm.award_date_estimate || undefined,
        win_probability: editForm.win_probability ?? undefined,
        notes: editForm.notes,
        vehicle_ids: editForm.vehicle_ids,
      };

      if (isNew) {
        const created = await api.createOpportunity(data);
        toast.success('Opportunity created');
        navigate(`/opportunities/${created.id}`);
      } else {
        const updated = await api.updateOpportunity(editForm.id, data);
        setOpp(updated);
        setIsEditing(false);
        setEditForm(null);
        toast.success('Opportunity updated');
      }
    } catch (error) {
      toast.error('Failed to save opportunity');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!opp) return;
    try {
      await api.deleteOpportunity(opp.id);
      toast.success('Opportunity deleted');
      navigate('/opportunities');
    } catch (error) {
      toast.error('Failed to delete');
      console.error(error);
    }
  };

  // Timeline handlers
  const handleAddEvent = async () => {
    if (!id || isNew || !newEvent.description.trim() || !newEvent.date) return;
    try {
      await api.createTimelineEvent(id, { opportunity_id: id, ...newEvent });
      setNewEvent({ date: '', event_type: 'note', description: '' });
      setShowEventForm(false);
      loadTabData();
      toast.success('Event added');
    } catch { toast.error('Failed to add event'); }
  };

  const handleDeleteEvent = async (eventId: string) => {
    if (!id) return;
    try {
      await api.deleteTimelineEvent(id, eventId);
      loadTabData();
    } catch { toast.error('Failed to delete event'); }
  };

  // Capture Notes handlers
  const handleSaveSection = async (section: string) => {
    if (!id || isNew) return;
    try {
      await api.upsertCaptureNote(id, section, sectionDraft);
      setCaptureNotes((prev) => ({ ...prev, [section]: sectionDraft }));
      setEditingSection(null);
      toast.success('Saved');
    } catch { toast.error('Failed to save'); }
  };

  // Attachment handlers
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !id || isNew) return;
    setIsUploading(true);
    try {
      await api.uploadAttachment(id, file);
      loadTabData();
      toast.success('File uploaded');
    } catch { toast.error('Failed to upload'); }
    finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteAttachment = async (attachmentId: string) => {
    if (!id) return;
    try {
      await api.deleteAttachment(id, attachmentId);
      loadTabData();
    } catch { toast.error('Failed to delete'); }
  };

  if (isLoading) {
    return <Layout><div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div></Layout>;
  }

  if (!opp && !isEditing) return null;
  const display = isEditing ? editForm : opp;
  if (!display) return null;

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: 'timeline', label: 'Timeline', icon: Clock },
    { key: 'capture', label: 'Capture Notes', icon: BookOpen },
    { key: 'teaming', label: 'Teaming', icon: Users },
    { key: 'attachments', label: 'Attachments', icon: Paperclip },
  ];

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 sm:gap-4 min-w-0">
            <Button variant="outline" size="icon" asChild className="shrink-0">
              <Link to="/opportunities"><ArrowLeft className="h-4 w-4" /></Link>
            </Button>
            <h2 className="text-xl sm:text-3xl font-bold tracking-tight truncate">
              {isNew ? 'New Opportunity' : display.title}
            </h2>
          </div>
          <div className="flex gap-2 self-end sm:self-auto">
            {isEditing ? (
              <>
                <Button size="sm" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</> : <><Save className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Save</span></>}
                </Button>
                {!isNew && (
                  <Button variant="outline" size="sm" onClick={() => { setEditForm(null); setIsEditing(false); }}>
                    <X className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Cancel</span>
                  </Button>
                )}
              </>
            ) : (
              <>
                <Button size="sm" onClick={() => { setEditForm({ ...opp! }); setIsEditing(true); }}>
                  <Edit className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Edit</span>
                </Button>
                <Button variant="destructive" size="sm" onClick={() => setShowDeleteConfirm(true)}>
                  <Trash2 className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Delete</span>
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Details Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Opportunity Details</CardTitle>
              {!isEditing && <Badge variant={getOpportunityStageBadge(display.stage)}>{display.stage}</Badge>}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEditing ? (
              <>
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input value={editForm!.title} onChange={(e) => setEditForm({ ...editForm!, title: e.target.value })} placeholder="Opportunity title" />
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg border border-border">
                  <Switch id="gov-contract" checked={editForm!.is_government_contract} onCheckedChange={(checked) => setEditForm({ ...editForm!, is_government_contract: checked })} />
                  <Label htmlFor="gov-contract" className="cursor-pointer">Government Contract</Label>
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea value={editForm!.description} onChange={(e) => setEditForm({ ...editForm!, description: e.target.value })} rows={3} placeholder="Describe the opportunity..." />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Agency</Label>
                    <Input value={editForm!.agency || ''} onChange={(e) => setEditForm({ ...editForm!, agency: e.target.value })} placeholder="e.g., Department of Defense" />
                  </div>
                  <div className="space-y-2">
                    <Label>Stage</Label>
                    <Select value={editForm!.stage} onValueChange={(v) => setEditForm({ ...editForm!, stage: v as api.Opportunity['stage'] })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {STAGES.map((s) => <SelectItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Estimated Value ($)</Label>
                    <Input type="number" value={editForm!.estimated_value ?? ''} onChange={(e) => setEditForm({ ...editForm!, estimated_value: e.target.value ? Number(e.target.value) : undefined })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Win Probability (%)</Label>
                    <Input type="number" min="0" max="100" value={editForm!.win_probability ?? ''} onChange={(e) => setEditForm({ ...editForm!, win_probability: e.target.value ? Number(e.target.value) : undefined })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Source</Label>
                    <Select value={editForm!.source || 'internal'} onValueChange={(v) => setEditForm({ ...editForm!, source: v as api.Opportunity['source'] })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {SOURCES.map((s) => <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {editForm!.is_government_contract && (
                  <>
                    <div className="border-t border-border pt-4">
                      <p className="text-sm font-medium text-muted-foreground mb-4">Government Contract Fields</p>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="space-y-2"><Label>Solicitation Number</Label><Input value={editForm!.solicitation_number || ''} onChange={(e) => setEditForm({ ...editForm!, solicitation_number: e.target.value })} /></div>
                      <div className="space-y-2"><Label>SAM.gov Notice ID</Label><Input value={editForm!.sam_gov_notice_id || ''} onChange={(e) => setEditForm({ ...editForm!, sam_gov_notice_id: e.target.value })} /></div>
                      <div className="space-y-2"><Label>NAICS Code</Label><Input value={editForm!.naics_code || ''} onChange={(e) => setEditForm({ ...editForm!, naics_code: e.target.value })} /></div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Set-Aside Type</Label>
                        <Select value={editForm!.set_aside_type || 'none'} onValueChange={(v) => setEditForm({ ...editForm!, set_aside_type: v as api.Opportunity['set_aside_type'] })}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>{SET_ASIDES.map((s) => <SelectItem key={s} value={s}>{formatSetAside(s)}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2"><Label>Submission Link</Label><Input value={editForm!.submission_link || ''} onChange={(e) => setEditForm({ ...editForm!, submission_link: e.target.value })} placeholder="https://..." /></div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2"><Label>Deadline</Label><Input type="date" value={editForm!.deadline?.split('T')[0] || ''} onChange={(e) => setEditForm({ ...editForm!, deadline: e.target.value || undefined })} /></div>
                      <div className="space-y-2"><Label>Expected Release Date</Label><Input type="date" value={editForm!.expected_release_date?.split('T')[0] || ''} onChange={(e) => setEditForm({ ...editForm!, expected_release_date: e.target.value || undefined })} /></div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2"><Label>Proposal Due Date</Label><Input type="date" value={editForm!.proposal_due_date?.split('T')[0] || ''} onChange={(e) => setEditForm({ ...editForm!, proposal_due_date: e.target.value || undefined })} /></div>
                      <div className="space-y-2"><Label>Award Date Estimate</Label><Input type="date" value={editForm!.award_date_estimate?.split('T')[0] || ''} onChange={(e) => setEditForm({ ...editForm!, award_date_estimate: e.target.value || undefined })} /></div>
                    </div>
                  </>
                )}
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea value={editForm!.notes} onChange={(e) => setEditForm({ ...editForm!, notes: e.target.value })} rows={4} />
                </div>
              </>
            ) : (
              <>
                {display.is_government_contract && (
                  <div className="mb-2"><Badge variant="outline">Government Contract</Badge></div>
                )}
                {display.description && (
                  <div><Label className="text-muted-foreground">Description</Label><p className="mt-1 whitespace-pre-wrap">{display.description}</p></div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                  <div><Label className="text-muted-foreground">Agency</Label><p className="mt-1">{display.agency || 'Not specified'}</p></div>
                  <div><Label className="text-muted-foreground">Estimated Value</Label><p className="mt-1 font-semibold text-lg">{formatCurrency(display.estimated_value)}</p></div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
                  <div><Label className="text-muted-foreground">Win Probability</Label><p className="mt-1 font-semibold">{display.win_probability !== undefined && display.win_probability !== null ? `${display.win_probability}%` : 'N/A'}</p></div>
                  {display.source && (<div><Label className="text-muted-foreground">Source</Label><p className="mt-1">{display.source.replace(/_/g, ' ')}</p></div>)}
                </div>
                {display.is_government_contract && (
                  <>
                    <div className="border-t border-border pt-4"><p className="text-sm font-medium text-muted-foreground mb-4">Government Contract Details</p></div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
                      <div><Label className="text-muted-foreground">Solicitation Number</Label><p className="mt-1">{display.solicitation_number || 'N/A'}</p></div>
                      <div><Label className="text-muted-foreground">SAM.gov Notice ID</Label><p className="mt-1">{display.sam_gov_notice_id || 'N/A'}</p></div>
                      <div><Label className="text-muted-foreground">NAICS</Label><p className="mt-1">{display.naics_code || 'N/A'}</p></div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                      <div><Label className="text-muted-foreground">Set-Aside</Label><p className="mt-1">{formatSetAside(display.set_aside_type)}</p></div>
                      {display.submission_link && (<div><Label className="text-muted-foreground">Submission Link</Label><p className="mt-1 break-all"><a href={display.submission_link} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{display.submission_link}</a></p></div>)}
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6">
                      <div><Label className="text-muted-foreground">Deadline</Label><p className="mt-1">{display.deadline ? new Date(display.deadline).toLocaleDateString() : 'N/A'}</p></div>
                      <div><Label className="text-muted-foreground">Expected Release</Label><p className="mt-1">{display.expected_release_date ? new Date(display.expected_release_date).toLocaleDateString() : 'N/A'}</p></div>
                      <div><Label className="text-muted-foreground">Proposal Due</Label><p className="mt-1 font-medium">{display.proposal_due_date ? new Date(display.proposal_due_date).toLocaleDateString() : 'N/A'}</p></div>
                      <div><Label className="text-muted-foreground">Award Estimate</Label><p className="mt-1">{display.award_date_estimate ? new Date(display.award_date_estimate).toLocaleDateString() : 'N/A'}</p></div>
                    </div>
                  </>
                )}
                {display.vehicles && display.vehicles.length > 0 && (
                  <div><Label className="text-muted-foreground">Contract Vehicles</Label><div className="flex gap-2 mt-1">{display.vehicles.map((v) => (<Badge key={v.id} variant="outline">{v.name}</Badge>))}</div></div>
                )}
                {display.notes && (<div><Label className="text-muted-foreground">Notes</Label><p className="mt-1 whitespace-pre-wrap">{display.notes}</p></div>)}
              </>
            )}
          </CardContent>
        </Card>

        {/* Tabs - only show when viewing an existing opportunity */}
        {!isNew && !isEditing && (
          <>
            <div className="flex gap-1 border-b border-border overflow-x-auto">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`flex items-center gap-2 px-3 sm:px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap ${
                      activeTab === tab.key
                        ? 'border-b-2 border-primary text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Timeline Tab */}
            {activeTab === 'timeline' && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Timeline</CardTitle>
                    <Button size="sm" onClick={() => setShowEventForm(!showEventForm)}>
                      <Plus className="mr-2 h-4 w-4" />Add Event
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {showEventForm && (
                    <div className="mb-6 p-4 rounded-lg border border-border space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Date</Label>
                          <Input type="date" value={newEvent.date} onChange={(e) => setNewEvent({ ...newEvent, date: e.target.value })} />
                        </div>
                        <div className="space-y-2">
                          <Label>Type</Label>
                          <Select value={newEvent.event_type} onValueChange={(v) => setNewEvent({ ...newEvent, event_type: v as api.OpportunityEvent['event_type'] })}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {EVENT_TYPES.map((t) => <SelectItem key={t} value={t}>{t.replace(/_/g, ' ')}</SelectItem>)}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Description</Label>
                        <Textarea value={newEvent.description} onChange={(e) => setNewEvent({ ...newEvent, description: e.target.value })} rows={2} />
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" onClick={handleAddEvent}>Save</Button>
                        <Button size="sm" variant="outline" onClick={() => setShowEventForm(false)}>Cancel</Button>
                      </div>
                    </div>
                  )}
                  {timeline.length > 0 ? (
                    <div className="relative">
                      <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
                      <div className="space-y-4">
                        {timeline.map((event) => (
                          <div key={event.id} className="relative pl-10">
                            <div className="absolute left-2.5 top-1.5 h-3 w-3 rounded-full border-2 border-primary bg-background" />
                            <div className="flex items-start justify-between p-3 rounded-lg border border-border">
                              <div>
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-sm font-medium">{new Date(event.date).toLocaleDateString()}</span>
                                  <Badge variant="outline" className="text-xs">{event.event_type.replace(/_/g, ' ')}</Badge>
                                </div>
                                <p className="text-sm">{event.description}</p>
                              </div>
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground" onClick={() => handleDeleteEvent(event.id)}>
                                <X className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-center text-muted-foreground py-8">No timeline events yet. Add events to track capture history.</p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Capture Notes Tab */}
            {activeTab === 'capture' && (
              <Card>
                <CardHeader>
                  <CardTitle>Capture Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {CAPTURE_SECTIONS.map(({ key, label }) => (
                      <div key={key} className="rounded-lg border border-border p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-sm">{label}</h4>
                          {editingSection === key ? (
                            <div className="flex gap-1">
                              <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => handleSaveSection(key)}>Save</Button>
                              <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => setEditingSection(null)}>Cancel</Button>
                            </div>
                          ) : (
                            <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => { setEditingSection(key); setSectionDraft(captureNotes[key] || ''); }}>
                              <Edit className="h-3 w-3 mr-1" />Edit
                            </Button>
                          )}
                        </div>
                        {editingSection === key ? (
                          <Textarea value={sectionDraft} onChange={(e) => setSectionDraft(e.target.value)} rows={4} className="text-sm" />
                        ) : (
                          <p className="text-sm text-muted-foreground whitespace-pre-wrap min-h-[60px]">
                            {captureNotes[key] || 'No notes yet.'}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Teaming Tab */}
            {activeTab === 'teaming' && (
              <Card>
                <CardHeader>
                  <CardTitle>Teaming Partners</CardTitle>
                </CardHeader>
                <CardContent>
                  {teamingRecords.length > 0 ? (
                    <div className="space-y-4">
                      {/* Simple visual graph */}
                      <div className="p-6 rounded-lg border border-border bg-muted/20">
                        <div className="flex flex-col items-center">
                          <div className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium text-sm">Your Company</div>
                          <div className="w-px h-6 bg-border" />
                          <div className="flex flex-wrap justify-center gap-6">
                            {teamingRecords.map((record) => (
                              <div key={record.id} className="flex flex-col items-center">
                                <div className="w-px h-4 bg-border" />
                                <div className="px-3 py-2 rounded-lg border border-border bg-background text-center">
                                  <p className="font-medium text-sm">{record.partner_account?.name || 'Unknown'}</p>
                                  <div className="flex gap-1 mt-1 justify-center">
                                    <Badge variant="outline" className="text-xs">{record.role.replace(/_/g, ' ')}</Badge>
                                    <Badge variant={record.status === 'active' || record.status === 'teaming_agreed' ? 'default' : 'secondary'} className="text-xs">
                                      {record.status.replace(/_/g, ' ')}
                                    </Badge>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                      {/* Detail list */}
                      <div className="space-y-2">
                        {teamingRecords.map((record) => (
                          <div key={record.id} className="flex items-center justify-between p-3 rounded-lg border border-border">
                            <div>
                              <p className="font-medium">{record.partner_account?.name || 'Unknown'}</p>
                              {record.notes && <p className="text-sm text-muted-foreground">{record.notes}</p>}
                            </div>
                            <div className="flex gap-2">
                              <Badge variant="outline">{record.role.replace(/_/g, ' ')}</Badge>
                              <Badge variant={record.status === 'active' || record.status === 'teaming_agreed' ? 'default' : 'secondary'}>
                                {record.status.replace(/_/g, ' ')}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-center text-muted-foreground py-8">No teaming partners yet. Add partners via the Teaming API.</p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Attachments Tab */}
            {activeTab === 'attachments' && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Attachments</CardTitle>
                    <div>
                      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileUpload} />
                      <Button size="sm" onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
                        {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                        Upload File
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {attachments.length > 0 ? (
                    <div className="space-y-2">
                      {attachments.map((att) => (
                        <div key={att.id} className="flex items-center justify-between p-3 rounded-lg border border-border">
                          <div className="flex items-center gap-3">
                            <FileText className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <p className="font-medium text-sm">{att.filename}</p>
                              <p className="text-xs text-muted-foreground">
                                {att.size ? `${(att.size / 1024).toFixed(1)} KB` : ''} {att.created_at && `· ${new Date(att.created_at).toLocaleDateString()}`}
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                              <a href={api.getAttachmentDownloadUrl(id!, att.id)} target="_blank" rel="noopener noreferrer">
                                <Download className="h-4 w-4" />
                              </a>
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDeleteAttachment(att.id)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-muted-foreground py-8">No attachments yet. Upload RFPs, proposals, or capture documents.</p>
                  )}
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        onConfirm={handleDelete}
        title="Delete Opportunity"
        description="Are you sure you want to delete this opportunity? This action cannot be undone."
        confirmLabel="Delete"
      />
    </Layout>
  );
}
