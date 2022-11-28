import { Component, OnInit } from '@angular/core';
import {ActivatedRoute, Router} from "@angular/router";
import {HttpClient, HttpHeaders} from "@angular/common/http";
import {MatDialog} from "@angular/material/dialog";
import {UserService} from "../../../../services/user.service";
import {FormBuilder, FormControl} from "@angular/forms";
import {AuthService} from "../../../../services/auth.service";
import {TranslateService} from "@ngx-translate/core";
import {NotificationService} from "../../../../services/notifications/notifications.service";
import {HistoryService} from "../../../../services/history.service";
import {SettingsService} from "../../../../services/settings.service";
import {LastUrlService} from "../../../../services/last-url.service";
import {PrivilegesService} from "../../../../services/privileges.service";
import {LocalStorageService} from "../../../../services/local-storage.service";
import {environment} from "../../../env";
import {catchError, finalize, tap} from "rxjs/operators";
import {of} from "rxjs";

@Component({
    selector: 'app-user-quota',
    templateUrl: './user-quota.component.html',
    styleUrls: ['./user-quota.component.scss']
})
export class UserQuotaComponent implements OnInit {
    headers             : HttpHeaders = this.authService.headers;
    loading             : boolean     = true;
    quotaNumber         : number      = 0;
    quotaEnabled        : boolean     = false;
    quotaUsersfiltered  : any[]       = [];
    usersControlSelect  : FormControl =  new FormControl();
    usersList           : any[]       = [];
    userQuotaConfigId   : number      = 0;

    constructor(
        public router: Router,
        private http: HttpClient,
        private dialog: MatDialog,
        private route: ActivatedRoute,
        public userService: UserService,
        private formBuilder: FormBuilder,
        private authService: AuthService,
        private translate: TranslateService,
        private notify: NotificationService,
        private historyService: HistoryService,
        public serviceSettings: SettingsService,
        public privilegesService: PrivilegesService,
    ) { }

    ngOnInit(): void {
        this.serviceSettings.init();

        this.http.get(environment['url'] + '/ws/users/list', {headers: this.authService.headers}).pipe(
            tap((data_users: any) => {
                this.usersList = data_users.users;
                this.http.get(environment['url'] + '/ws/config/getConfiguration/userQuota', {headers: this.authService.headers}).pipe(
                    tap((data: any) => {
                        this.userQuotaConfigId = data.configuration[0].id;
                        if (data.configuration.length === 1) {
                            this.quotaEnabled = data.configuration[0].data.value.enabled;
                            this.quotaNumber = data.configuration[0].data.value.quota;
                            data.configuration[0].data.value.users_filtered.forEach((elem: any) => {
                                this.usersList.forEach((user: any) => {
                                    if (user['username'] === elem.trim()) {
                                        this.quotaUsersfiltered.push(user['id']);
                                    }
                                });
                                this.usersControlSelect.setValue(this.quotaUsersfiltered);
                            });
                        }
                    }),
                    catchError((err: any) => {
                        console.debug(err);
                        this.notify.handleErrors(err);
                        return of(false);
                    })
                ).subscribe();
            }),
            finalize(() => {this.loading = false;}),
            catchError((err: any) => {
                console.debug(err);
                this.notify.handleErrors(err);
                return of(false);
            })
        ).subscribe();
    }

    updateQuotaNumber() {
        this.loading = true;
        const data: any = {
            'value': {
                'enabled': this.quotaEnabled,
                'quota': this.quotaNumber,
                'users_filtered': []
            }
        };
        this.usersControlSelect.value.forEach((user_id: any) => {
            this.usersList.forEach((user: any) => {
               if (user['id'] === user_id) {
                   data['value']['users_filtered'].push(user['username']);
               }
            });
        });

        this.http.put(environment['url'] + '/ws/config/updateConfiguration/' + this.userQuotaConfigId,
            {'data': data}, {headers: this.authService.headers}).pipe(
            tap(() => {
                this.notify.success(this.translate.instant('USER-QUOTA.updated'));
                this.historyService.addHistory('general', 'mailcollect', this.translate.instant('HISTORY-DESC.user_quota_updated'));
            }),
            finalize(() => this.loading = false),
            catchError((err: any) => {
                console.debug(err);
                this.notify.handleErrors(err);
                return of(false);
            })
        ).subscribe();
    }
}
