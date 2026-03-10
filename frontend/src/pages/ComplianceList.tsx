import { useState, useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import * as api from '@/lib/api';
import { getComplianceStatusBadge, formatCertificationType } from '@/lib/badges';
import { Plus, Loader2, AlertTriangle, ShieldCheck, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const CERT_TYPES = ['small_business', '8a', 'hubzone', 'wosb', 'sdvosb', 'edwosb'] as const;
const STATUSES = ['active', 'expiring_soon', 'expired', 'pending'] as const;

export default function ComplianceList() {
  const [records, setRecords] = useState<api.ComplianceRecord[]>([]);
  const [expiring, setExpiring] = useState<api.ComplianceRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [newRecord, setNewRecord] = useState<api.ComplianceCreate>({
    certification_type: 'small_business',
    status: 'active',
    notes: '',
  });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [recordsData, expiringData] = await Promise.all([
        api.getComplianceRecords(),
        api.getExpiringCertifications(90),
      ]);
      setRecords(recordsData);
      setExpiring(expiringData);
    } catch (error) {
      toast.error('Failed to load compliance data');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdd = async () => {
    try {
      await api.createCompliance(newRecord);
      toast.success('Certification added');
      setShowAddDialog(false);
      setNewRecord({ certification_type: 'small_business', status: 'active', notes: '' });
      loadData();
    } catch (error) {
      toast.error('Failed to add certification');
      console.error(error);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await api.deleteCompliance(deleteId);
      toast.success('Certification deleted');
      setDeleteId(null);
      loadData();
    } catch (error) {
      toast.error('Failed to delete');
      console.error(error);
    }
  };

  if (isLoading) {
    return <Layout><div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div></Layout>;
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Compliance & Certifications</h2>
            <p className="text-muted-foreground">Track certifications & expiration dates</p>
          </div>
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button><Plus className="mr-2 h-4 w-4" />Add Certification</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Certification</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Certification Type</Label>
                  <Select value={newRecord.certification_type} onValueChange={(v) => setNewRecord({ ...newRecord, certification_type: v as api.ComplianceRecord['certification_type'] })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {CERT_TYPES.map((t) => <SelectItem key={t} value={t}>{formatCertificationType(t)}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Issued By</Label>
                  <Input value={newRecord.issued_by || ''} onChange={(e) => setNewRecord({ ...newRecord, issued_by: e.target.value })} placeholder="e.g., U.S. Small Business Administration" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Issue Date</Label>
                    <Input type="date" value={newRecord.issue_date || ''} onChange={(e) => setNewRecord({ ...newRecord, issue_date: e.target.value || undefined })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Expiration Date</Label>
                    <Input type="date" value={newRecord.expiration_date || ''} onChange={(e) => setNewRecord({ ...newRecord, expiration_date: e.target.value || undefined })} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={newRecord.status} onValueChange={(v) => setNewRecord({ ...newRecord, status: v as api.ComplianceRecord['status'] })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {STATUSES.map((s) => <SelectItem key={s} value={s}>{s.replace(/_/g, ' ')}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea value={newRecord.notes} onChange={(e) => setNewRecord({ ...newRecord, notes: e.target.value })} rows={3} />
                </div>
                <Button onClick={handleAdd} className="w-full">Add Certification</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {expiring.length > 0 && (
          <Card className="border-yellow-500/50 bg-yellow-500/5">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
                <CardTitle className="text-yellow-700">Expiring Soon</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {expiring.map((r) => (
                  <div key={r.id} className="flex items-center justify-between p-3 rounded-lg border border-yellow-500/30">
                    <div>
                      <p className="font-medium">{formatCertificationType(r.certification_type)}</p>
                      <p className="text-sm text-muted-foreground">
                        Expires: {r.expiration_date ? new Date(r.expiration_date).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                    <Badge variant="secondary">Expiring</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <div className="space-y-4">
          {records.length > 0 ? (
            records.map((record) => (
              <Card key={record.id} className="p-6">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-3">
                    <ShieldCheck className="h-5 w-5 mt-0.5 text-muted-foreground shrink-0" />
                    <div>
                      <h3 className="font-semibold">{formatCertificationType(record.certification_type)}</h3>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-sm text-muted-foreground">
                        {record.issued_by && <span>Issued by: {record.issued_by}</span>}
                        {record.issue_date && <span>Issued: {new Date(record.issue_date).toLocaleDateString()}</span>}
                        {record.expiration_date && <span>Expires: {new Date(record.expiration_date).toLocaleDateString()}</span>}
                      </div>
                      {record.notes && <p className="mt-2 text-sm text-muted-foreground">{record.notes}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 self-start">
                    <Badge variant={getComplianceStatusBadge(record.status)}>
                      {record.status.replace(/_/g, ' ')}
                    </Badge>
                    <Button variant="ghost" size="icon" onClick={() => setDeleteId(record.id)}>
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          ) : (
            <Card className="p-12 text-center">
              <p className="text-muted-foreground">No certifications tracked yet.</p>
            </Card>
          )}
        </div>
      </div>
      <ConfirmDialog open={!!deleteId} onOpenChange={(open) => { if (!open) setDeleteId(null); }} onConfirm={handleDelete}
        title="Delete Certification" description="Are you sure? This action cannot be undone." confirmLabel="Delete" />
    </Layout>
  );
}
