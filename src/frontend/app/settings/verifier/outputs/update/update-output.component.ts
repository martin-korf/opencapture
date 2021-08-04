import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from "@angular/router";
import {UserService} from "../../../../../services/user.service";
import {TranslateService} from "@ngx-translate/core";
import {NotificationService} from "../../../../../services/notifications/notifications.service";
import {SettingsService} from "../../../../../services/settings.service";
import {PrivilegesService} from "../../../../../services/privileges.service";
import {HttpClient, HttpHeaders} from "@angular/common/http";
import {FormBuilder, FormControl} from "@angular/forms";
import {AuthService} from "../../../../../services/auth.service";
import {API_URL} from "../../../../env";
import {catchError, finalize, tap} from "rxjs/operators";
import {of} from "rxjs";

@Component({
    selector: 'app-update',
    templateUrl: './update-output.component.html',
    styleUrls: ['./update-output.component.scss']
})
export class UpdateOutputComponent implements OnInit {
    headers             : HttpHeaders   = this.authService.headers;
    loading             : boolean       = true;
    outputId            : any;
    output              : any;
    outputsTypes        : any[]          = [];
    outputsTypesForm    : any[]          = [];
    selectedOutputType  : any;
    outputForm          : any[]          = [
        {
            id: 'output_type_id',
            label: this.translate.instant('HEADER.output_type'),
            type: 'select',
            control: new FormControl(),
            required: true,
            values: this.outputsTypes
        },
        {
            id: 'output_label',
            label: this.translate.instant('HEADER.label'),
            type: 'text',
            control: new FormControl(),
            required: true,
        }
    ];
    constructor(
        private http: HttpClient,
        public router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private authService: AuthService,
        public userService: UserService,
        public translate: TranslateService,
        private notify: NotificationService,
        public serviceSettings: SettingsService,
        public privilegesService: PrivilegesService
    ) {}

    ngOnInit(): void {
        this.serviceSettings.init()
        this.outputId = this.route.snapshot.params['id'];

        this.http.get(API_URL + '/ws/outputs/getById/' + this.outputId, {headers: this.authService.headers}).pipe(
            tap((data: any) => {
                this.output = data;
                for (let field in data) {
                    if (data.hasOwnProperty(field)) {
                        this.outputForm.forEach(element => {
                            if (element.id == field) {
                                if (element.id === 'output_type_id') this.selectedOutputType = data[field];
                                element.control.setValue(data[field]);
                            }
                        });
                    }
                }
                this.http.get(API_URL + '/ws/outputs/getOutputsType', {headers: this.authService.headers}).pipe(
                    tap((data: any) => {
                        this.outputsTypes = data.outputs_types;
                        for (let _output of this.outputsTypes) {
                            this.outputsTypesForm[_output.type_id] = [];
                            for (let option of _output.data.options) {
                                this.outputsTypesForm[_output.type_id].push([
                                    {
                                        id: option.id,
                                        label: option.label,
                                        type: option.type,
                                        control: new FormControl(),
                                        required: option.required,
                                    }
                                ]);
                            }
                        }
                    }),
                    catchError((err: any) => {
                        console.debug(err);
                        this.notify.handleErrors(err);
                        this.router.navigate(['/settings/verifier/outputs']).then()
                        return of(false);
                    })
                ).subscribe();
            }),
            finalize(() => this.loading = false),
            catchError((err: any) => {
                console.debug(err);
                this.notify.handleErrors(err);
                this.router.navigate(['/settings/verifier/outputs']).then()
                return of(false);
            })
        ).subscribe();
    }

    getErrorMessage(field: any) {
        let error = undefined;
        this.outputForm.forEach(element => {
            if (element.id == field) {
                if (element.required) {
                    error = this.translate.instant('AUTH.field_required');
                }
            }
        })
        return error
    }

    changeOutputType(event: any) {
        this.selectedOutputType = event.value;
    }

    isValidForm() {
        let state = true;
        this.outputForm.forEach(element => {
            if (element.control.status !== 'DISABLED' && element.control.status !== 'VALID') {
                state = false;
            }
            element.control.markAsTouched();
        });
        return state;
    }

    onSubmit() {
        if (this.isValidForm()) {
            const output: any = {};
            this.outputForm.forEach(element => {
                output[element.id] = element.control.value;
            });
        }
    }
}
