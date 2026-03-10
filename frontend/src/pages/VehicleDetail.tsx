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
import { formatCurrency } from '@/lib/badges';
import { ArrowLeft, Trash2, Save, Loader2, Edit, X } from 'lucide-react';
import { toast } from 'sonner';

const emptyVehicle: api.ContractVehicle = {
  id: '', name: '', notes: '', created_at: '', updated_at: '',
};

export default function VehicleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [vehicle, setVehicle] = useState<api.ContractVehicle | null>(null);
  const [editForm, setEditForm] = useState<api.ContractVehicle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const loadData = useCallback(async () => {
    try {
      if (id === 'new') {
        setVehicle(emptyVehicle);
        setEditForm({ ...emptyVehicle });
        setIsEditing(true);
      } else if (id) {
        const data = await api.getVehicle(id);
        setVehicle(data);
      }
    } catch (error) {
      toast.error('Failed to load vehicle');
      console.error(error);
      navigate('/vehicles');
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
      const data: api.ContractVehicleCreate = {
        name: editForm.name,
        agency: editForm.agency || undefined,
        contract_number: editForm.contract_number || undefined,
        expiration_date: editForm.expiration_date || undefined,
        ceiling_value: editForm.ceiling_value || undefined,
        prime_or_sub: editForm.prime_or_sub || undefined,
        notes: editForm.notes,
      };

      if (id === 'new') {
        const created = await api.createVehicle(data);
        toast.success('Vehicle created');
        navigate(`/vehicles/${created.id}`);
      } else {
        const updated = await api.updateVehicle(editForm.id, data);
        setVehicle(updated);
        setIsEditing(false);
        setEditForm(null);
        toast.success('Vehicle updated');
      }
    } catch (error) {
      toast.error('Failed to save vehicle');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!vehicle) return;
    try {
      await api.deleteVehicle(vehicle.id);
      toast.success('Vehicle deleted');
      navigate('/vehicles');
    } catch (error) {
      toast.error('Failed to delete');
      console.error(error);
    }
  };

  if (isLoading) {
    return <Layout><div className="flex items-center justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div></Layout>;
  }

  if (!vehicle && !isEditing) return null;
  const display = isEditing ? editForm : vehicle;
  if (!display) return null;

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 sm:gap-4 min-w-0">
            <Button variant="outline" size="icon" asChild className="shrink-0">
              <Link to="/vehicles"><ArrowLeft className="h-4 w-4" /></Link>
            </Button>
            <h2 className="text-xl sm:text-3xl font-bold tracking-tight truncate">
              {id === 'new' ? 'New Contract Vehicle' : display.name}
            </h2>
          </div>
          <div className="flex gap-2 self-end sm:self-auto">
            {isEditing ? (
              <>
                <Button size="sm" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</> : <><Save className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Save</span></>}
                </Button>
                {id !== 'new' && <Button variant="outline" size="sm" onClick={() => { setEditForm(null); setIsEditing(false); }}><X className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Cancel</span></Button>}
              </>
            ) : (
              <>
                <Button size="sm" onClick={() => { setEditForm({ ...vehicle! }); setIsEditing(true); }}><Edit className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Edit</span></Button>
                <Button variant="destructive" size="sm" onClick={() => setShowDeleteConfirm(true)}><Trash2 className="h-4 w-4 sm:mr-2" /><span className="hidden sm:inline">Delete</span></Button>
              </>
            )}
          </div>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Vehicle Information</CardTitle>
              {!isEditing && display.prime_or_sub && (
                <Badge variant={display.prime_or_sub === 'prime' ? 'default' : 'outline'}>{display.prime_or_sub}</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEditing ? (
              <>
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input value={editForm!.name} onChange={(e) => setEditForm({ ...editForm!, name: e.target.value })} placeholder="Vehicle name" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Agency</Label>
                    <Input value={editForm!.agency || ''} onChange={(e) => setEditForm({ ...editForm!, agency: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Contract Number</Label>
                    <Input value={editForm!.contract_number || ''} onChange={(e) => setEditForm({ ...editForm!, contract_number: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Ceiling Value ($)</Label>
                    <Input type="number" value={editForm!.ceiling_value ?? ''} onChange={(e) => setEditForm({ ...editForm!, ceiling_value: e.target.value ? Number(e.target.value) : undefined })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Expiration Date</Label>
                    <Input type="date" value={editForm!.expiration_date?.split('T')[0] || ''} onChange={(e) => setEditForm({ ...editForm!, expiration_date: e.target.value || undefined })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Prime or Sub</Label>
                    <Select value={editForm!.prime_or_sub || 'prime'} onValueChange={(v) => setEditForm({ ...editForm!, prime_or_sub: v as 'prime' | 'sub' })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="prime">Prime</SelectItem>
                        <SelectItem value="sub">Sub</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
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
                    <Label className="text-muted-foreground">Agency</Label>
                    <p className="mt-1">{display.agency || 'N/A'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Contract Number</Label>
                    <p className="mt-1">{display.contract_number || 'N/A'}</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <Label className="text-muted-foreground">Ceiling Value</Label>
                    <p className="mt-1 font-semibold">{formatCurrency(display.ceiling_value)}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Expiration Date</Label>
                    <p className="mt-1">{display.expiration_date ? new Date(display.expiration_date).toLocaleDateString() : 'N/A'}</p>
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
      <ConfirmDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm} onConfirm={handleDelete}
        title="Delete Vehicle" description="Are you sure? This action cannot be undone." confirmLabel="Delete" />
    </Layout>
  );
}
