/** This file is part of Open-Capture.

 Open-Capture is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Open-Capture is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Open-Capture. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.

 @dev : Tristan Coulange <tristan.coulange@free.fr> */

import { Component, OnInit } from '@angular/core';
import { HttpClient } from "@angular/common/http";
import { MatDialog } from '@angular/material/dialog';
import { ActivatedRoute, Router } from "@angular/router";
import { FormBuilder, FormGroup } from "@angular/forms";
import { AuthService } from "../../../../../services/auth.service";
import { UserService } from "../../../../../services/user.service";
import { TranslateService } from "@ngx-translate/core";
import { NotificationService } from "../../../../../services/notifications/notifications.service";
import { SettingsService } from "../../../../../services/settings.service";
import { PrivilegesService } from "../../../../../services/privileges.service";
import { environment } from "../../../../env";
import { catchError, of, tap } from "rxjs";
import { Sort } from "@angular/material/sort";
import { finalize } from "rxjs/operators";
import { ConfirmDialogComponent } from "../../../../../services/confirm-dialog/confirm-dialog.component";
import { HistoryService } from "../../../../../services/history.service";

@Component({
  selector: 'app-artificial-intelligence',
  templateUrl: './artificial-intelligence.component.html',
  styleUrls: ['./artificial-intelligence.component.scss']
})

export class ListAiModelComponent implements OnInit {
    loading             : boolean   = true;
    modelsList          : any       = [];
    showResponse        : boolean   = false;
    DocToPredSelected   : boolean   = true;
    isPredicting        : boolean   = false;
    displayedColumns    : string[]  = ['id', 'model_path', 'train_time', 'type','accuracy_score','documents', 'min_proba', 'actions'];
    offset              : number    = 0;
    pageSize            : number    = 10;
    pageIndex           : number    = 0;
    total               : number    = 0;
    clickedRow          : object    = {};
    prediction          : any       = [];
    uploadForm!         : FormGroup;

    constructor(
        private http: HttpClient,
        private dialog: MatDialog,
        public router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private authService: AuthService,
        public userService: UserService,
        public translate: TranslateService,
        private notify: NotificationService,
        public serviceSettings: SettingsService,
        private historyService: HistoryService,
        public privilegesService: PrivilegesService,
    ) { }

    ngOnInit() {
        this.serviceSettings.init();
        this.retrieveModels();
        this.uploadForm = this.formBuilder.group({file: ['']});
    }

    retrieveModels(offset?: number, size?: number) {
        this.http.get(environment['url'] + '/ws/ai/getAIModels', {headers: this.authService.headers}).pipe(
            tap((data: any) => {
                this.modelsList = data.models;
                for (let i = 0; i < this.modelsList.length; i++) {
                    let tmp_doc = "";
                    for (let j = 0; j < this.modelsList[i].documents.length; j++) {
                        tmp_doc += this.modelsList[i].documents[j].folder + ", ";
                        if(j === this.modelsList[i].documents.length - 1) {
                            tmp_doc = tmp_doc.slice(0, -2);
                        }
                    }
                    this.modelsList[i].documents = [tmp_doc];
                }
                this.total = this.modelsList.length;
                if (offset !== undefined && size !== undefined) {
                    this.modelsList = this.modelsList.slice(offset, offset + size);
                } else {
                    this.modelsList = this.modelsList.slice(0,10);
                }
            }),
            finalize(() => this.loading = false),
            catchError((err: any) => {
                console.debug(err);
                return of(false);
            })
        ).subscribe();
    }

    sortData(sort: Sort) {
        const data = this.modelsList.slice();
        if (!sort.active || sort.direction === '') {
            this.modelsList = data;
            return;
        }

        this.modelsList = data.sort((a: any, b: any) => {
            const isAsc = sort.direction === 'asc';
            switch (sort.active) {
                case 'id': return this.compare(a.id, b.id, isAsc);
                case 'model_path': return this.compare(a.path, b.path, isAsc);
                case 'train_time': return this.compare(a.train_time, b.train_time, isAsc);
                case 'type': return this.compare(a.type, b.type, isAsc);
                case 'accuracy_score': return this.compare(a.accuracy, b.accuracy, isAsc);
                case 'doc_types': return this.compare(a.doctypes, b.doctypes, isAsc);
                case 'status': return this.compare(a.status, b.status, isAsc);
                case 'min_proba': return this.compare(a.min_proba, b.min_proba, isAsc);
                default:
                    return 0;
            }
        });
    }

    compare(a: number | string, b: number | string, isAsc: boolean) {
        return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
    }

    selectRow(row : object) {
        this.clickedRow = row;
    }

    displaySelectedRowId() {
        const disp = Object.values(this.clickedRow)[2];
        if (disp) {
            return(disp);
        }
        else return 0;
    }

    deleteConfirmDialog(modelId: number, model: string) {
        const dialogRef = this.dialog.open(ConfirmDialogComponent, {
            data: {
                confirmTitle: this.translate.instant('GLOBAL.confirm'),
                confirmText: this.translate.instant('ARTIFICIAL-INTELLIGENCE.confirm_delete', {"model": model}),
                confirmButton: this.translate.instant('GLOBAL.delete'),
                confirmButtonColor: "warn",
                cancelButton: this.translate.instant('GLOBAL.cancel'),
            },
            width: "600px",
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.deleteOutput(modelId);
                this.historyService.addHistory('splitter', 'delete_model', this.translate.instant('HISTORY-DESC.delete-model', {model: model}));
            }
        });
    }

    deleteOutput(modelId: number) {
        if (modelId !== undefined) {
            this.http.delete(environment['url'] + '/ws/ai/delete/' + modelId, {headers: this.authService.headers}).pipe(
                tap(() => {
                    this.retrieveModels();
                    this.notify.success(this.translate.instant('ARTIFICIAL-INTELLIGENCE.model_deleted'));
                }),
                catchError((err: any) => {
                    console.debug(err);
                    this.notify.handleErrors(err);
                    return of(false);
                })
            ).subscribe();
        }
    }

    onPageChange(event: any) {
        this.pageSize = event.pageSize;
        this.offset = this.pageSize * (event.pageIndex);
        this.retrieveModels(this.offset, this.pageSize);
    }

    onFileSelect(event: Event) {
        const target = event.target as HTMLInputElement;
        if (target.files?.length) {
            const file = target?.files[0];
            this.uploadForm.get('file')?.setValue(file);
            this.DocToPredSelected = true;
        }
    }

    onSubmit() {
        this.showResponse = false;
        const formData = new FormData();
        const disp = Object.values(this.clickedRow)[4];
        if (this.uploadForm.get('file')?.value) {
            this.isPredicting = true;
            formData.append('file', this.uploadForm.get('file')?.value);

            this.http.post<any>(environment['url'] + '/ws/ai/testModel/' + disp, formData, {headers: this.authService.headers}).pipe(
                tap((res) => this.onResponse(res)),
                catchError((err: any) => {
                    console.debug(err);
                    this.notify.error(this.translate.instant('ARTIFICIAL-INTELLIGENCE.model_not_found'));
                    this.isPredicting = false;
                    return of(false);
                })
            ).subscribe();
        }
        else {
            this.DocToPredSelected = false;
        }
    }

    onResponse(res: any) {
        this.prediction = res;
        this.showResponse = true;
        this.isPredicting = false;
    }
}