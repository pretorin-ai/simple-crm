import { useState, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import * as api from '@/lib/api';
import { Loader2, Search, Mail, Building2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface ImportGmailContactsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportComplete: () => void;
}

export function ImportGmailContactsDialog({
  open,
  onOpenChange,
  onImportComplete,
}: ImportGmailContactsDialogProps) {
  const [step, setStep] = useState<'loading' | 'select' | 'importing' | 'done' | 'error'>('loading');
  const [contacts, setContacts] = useState<api.GoogleContactPreview[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [importResult, setImportResult] = useState<api.GoogleContactImportResponse | null>(null);

  const loadContacts = async () => {
    setStep('loading');
    setSearchQuery('');
    setSelected(new Set());
    setErrorMessage('');
    try {
      const result = await api.getGmailContactsPreview();
      setContacts(result.contacts);
      // Pre-select contacts that don't already exist
      const newSelected = new Set<string>();
      result.contacts.forEach((c) => {
        if (!c.already_exists) {
          newSelected.add(c.google_resource_name);
        }
      });
      setSelected(newSelected);
      setStep('select');
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to fetch Google Contacts';
      setErrorMessage(msg);
      setStep('error');
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      loadContacts();
    } else {
      setStep('loading');
      setContacts([]);
      setSelected(new Set());
    }
    onOpenChange(newOpen);
  };

  const filteredContacts = useMemo(() => {
    if (!searchQuery) return contacts;
    const q = searchQuery.toLowerCase();
    return contacts.filter(
      (c) =>
        c.first_name.toLowerCase().includes(q) ||
        c.last_name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        c.organization.toLowerCase().includes(q),
    );
  }, [contacts, searchQuery]);

  const selectableContacts = useMemo(
    () => filteredContacts.filter((c) => !c.already_exists),
    [filteredContacts],
  );

  const toggleContact = (resourceName: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(resourceName)) {
        next.delete(resourceName);
      } else {
        next.add(resourceName);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectableContacts.every((c) => selected.has(c.google_resource_name))) {
      // Deselect all visible selectable
      setSelected((prev) => {
        const next = new Set(prev);
        selectableContacts.forEach((c) => next.delete(c.google_resource_name));
        return next;
      });
    } else {
      // Select all visible selectable
      setSelected((prev) => {
        const next = new Set(prev);
        selectableContacts.forEach((c) => next.add(c.google_resource_name));
        return next;
      });
    }
  };

  const handleImport = async () => {
    const toImport = contacts.filter(
      (c) => selected.has(c.google_resource_name) && !c.already_exists,
    );
    if (toImport.length === 0) {
      toast.error('No contacts selected for import');
      return;
    }

    setStep('importing');
    try {
      const items: api.GoogleContactImportItem[] = toImport.map((c) => ({
        first_name: c.first_name,
        last_name: c.last_name,
        email: c.email,
        phone: c.phone,
        organization: c.organization,
        title: c.title,
        contact_type: 'individual',
        status: 'cold',
      }));
      const result = await api.importGmailContacts(items);
      setImportResult(result);
      setStep('done');
      if (result.imported > 0) {
        toast.success(`Imported ${result.imported} contact${result.imported !== 1 ? 's' : ''}`);
        onImportComplete();
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Import failed';
      toast.error(msg);
      setStep('select');
    }
  };

  const allVisibleSelected =
    selectableContacts.length > 0 &&
    selectableContacts.every((c) => selected.has(c.google_resource_name));

  const selectedCount = contacts.filter(
    (c) => selected.has(c.google_resource_name) && !c.already_exists,
  ).length;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Import Gmail Contacts</DialogTitle>
          <DialogDescription>
            {step === 'select' && `${contacts.length} contacts found. Select which ones to import.`}
            {step === 'loading' && 'Fetching your Google Contacts...'}
            {step === 'importing' && 'Importing contacts...'}
            {step === 'done' && 'Import complete!'}
            {step === 'error' && 'Failed to load contacts'}
          </DialogDescription>
        </DialogHeader>

        {step === 'loading' && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {step === 'error' && (
          <div className="flex flex-col items-center gap-4 py-8">
            <AlertCircle className="h-10 w-10 text-destructive" />
            <p className="text-sm text-muted-foreground text-center max-w-sm">
              {errorMessage}
            </p>
            <p className="text-xs text-muted-foreground text-center">
              If you recently connected Gmail, you may need to reconnect to grant contacts access.
            </p>
            <Button variant="outline" onClick={loadContacts}>
              Try Again
            </Button>
          </div>
        )}

        {step === 'select' && (
          <>
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search contacts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button variant="outline" size="sm" onClick={toggleAll}>
                {allVisibleSelected ? 'Deselect All' : 'Select All'}
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0 max-h-[50vh] border rounded-md divide-y">
              {filteredContacts.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground">
                  No contacts found matching your search.
                </div>
              ) : (
                filteredContacts.map((contact) => (
                  <label
                    key={contact.google_resource_name}
                    className={`flex items-center gap-3 p-3 hover:bg-muted/50 cursor-pointer ${
                      contact.already_exists ? 'opacity-50' : ''
                    }`}
                  >
                    <Checkbox
                      checked={selected.has(contact.google_resource_name)}
                      onCheckedChange={() => toggleContact(contact.google_resource_name)}
                      disabled={contact.already_exists}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm truncate">
                          {contact.first_name} {contact.last_name}
                        </span>
                        {contact.already_exists && (
                          <Badge variant="secondary" className="text-xs shrink-0">
                            Already exists
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                        <span className="flex items-center gap-1 truncate">
                          <Mail className="h-3 w-3 shrink-0" />
                          {contact.email}
                        </span>
                        {contact.organization && (
                          <span className="flex items-center gap-1 truncate">
                            <Building2 className="h-3 w-3 shrink-0" />
                            {contact.organization}
                          </span>
                        )}
                      </div>
                    </div>
                  </label>
                ))
              )}
            </div>
          </>
        )}

        {step === 'importing' && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {step === 'done' && importResult && (
          <div className="py-4 space-y-2 text-sm">
            <p>Imported: <strong>{importResult.imported}</strong> contact{importResult.imported !== 1 ? 's' : ''}</p>
            {importResult.skipped > 0 && (
              <p>Skipped (already exist): <strong>{importResult.skipped}</strong></p>
            )}
            {importResult.errors.length > 0 && (
              <div>
                <p className="text-destructive">Errors:</p>
                <ul className="list-disc pl-5">
                  {importResult.errors.map((err, i) => (
                    <li key={i} className="text-destructive">{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {(step === 'select' || step === 'done') && (
          <DialogFooter>
            {step === 'select' && (
              <>
                <Button variant="outline" onClick={() => handleOpenChange(false)}>
                  Cancel
                </Button>
                <Button onClick={handleImport} disabled={selectedCount === 0}>
                  Import {selectedCount} Contact{selectedCount !== 1 ? 's' : ''}
                </Button>
              </>
            )}
            {step === 'done' && (
              <Button onClick={() => handleOpenChange(false)}>Close</Button>
            )}
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
