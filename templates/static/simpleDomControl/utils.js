(function (utils) {

    var commend_reg = /((\/\/.*$)|(\/\*[\s\S]*?\*\/))/mg;
    var arg_names_reg = /([^\s,]+)/g;
    var uuidIndex = 0;

    utils.copyTextToClipboard = function (text) {
        var textArea = document.createElement("textarea");

        textArea.style.position = 'fixed';
        textArea.style.top = 0;
        textArea.style.left = 0;

        // Ensure it has a small width and height. Setting to 1px / 1em
        // doesn't work as this gives a negative w/h on some browsers.
        textArea.style.width = '2em';
        textArea.style.height = '2em';

        // We don't need padding, reducing the size if it does flash render.
        textArea.style.padding = 0;

        // Clean up any borders.
        textArea.style.border = 'none';
        textArea.style.outline = 'none';
        textArea.style.boxShadow = 'none';

        // Avoid flash of white box if rendered for any reason.
        textArea.style.background = 'transparent';


        textArea.value = text;

        document.body.appendChild(textArea);

        textArea.select();

        try {
            var successful = document.execCommand('copy');
            var msg = successful ? 'successful' : 'unsuccessful';
        } catch (err) {
            window.prompt("Copy to clipboard: Ctrl+C, Enter", text);
        }

        document.body.removeChild(textArea);
    };

    utils.getParamsNameOfFunction = function (func) {
        var fnstr = func.toString().replace(commend_reg, '');
        var result = fnstr.slice(fnstr.indexOf('(') + 1, fnstr.indexOf(')')).match(arg_names_reg);
        if (!result) {
            return [];
        }

        return result;
    };

    utils.guid = function () {
        function s4() {
            return Math.floor((1 + Math.random()) * 0x10000)
                .toString(16)
                .substring(1);
        }

        return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
            s4() + '-' + s4() + s4() + s4() + (uuidIndex++);
    };

    /**
     * This is the function that will take care of image extracting and
     * setting proper filename for the download.
     * IMPORTANT: Call it from within a onclick event.
     */
    utils.downloadCanvas = function (canvas, filename) {
        var link = document.createElement('a');
        document.body.appendChild(link);
        link.href = canvas.toDataURL();
        link.download = filename;
        link.click();
        setTimeout(function () {
            document.body.removeChild(link);
        }, 1);
    };

    utils.downloadFile = function (url) {
        //url and data options required
        if (url) {
            //data can be string of parameters or array/object

            var inputs = '';
            for (var i = 0; i < whiteList.length; i++) {
                inputs += '<input type="hidden" name="whiteList[]" value="' + whiteList[i] + '" />';
            }

            inputs += '<input type="hidden" name="withHeader" value="' + withHeader + '" />';
            //send request
            $('<form action="' + url + '" method="get">' + inputs + '</form>')
                .appendTo('body').submit().remove();

        }
    };


    utils.uuidIdAndFor = function ($content) {
        var uuid = utils.guid();
        $content.find('.label-for-change').each(function () {
            var $this = $(this);
            var forIdVal = $this.attr('for');
            var newId = '_' + forIdVal + uuid;
            $content.find('#' + forIdVal).attr('id', newId);
            $this.attr('for', newId);
        });
    };

    utils.uuidNameOfRadio = function ($content) {
        var $collection = {};
        $content.find('input[type=radio]').each(function () {
            var $this = $(this), name = $this.attr('name');
            if (!$collection[name]) {
                $collection[name] = [];
            }

            $collection[name].push($this);
        });

        var uuid = utils.guid();
        for (var name in $collection) {
            if ($collection.hasOwnProperty(name)) {
                for (var i = 0; i < $collection[name].length; i++) {
                    $collection[name][i].attr('name', '_' + name + '_' + uuid);
                }
            }
        }
    };

    utils.getCursorPosition = function (input) {
        if (input) {
            if ("selectionStart" in input && document.activeElement == input) {
                return {
                    start: input.selectionStart,
                    end: input.selectionEnd
                };
            } else if (input.createTextRange) {
                var sel = document.selection.createRange();
                if (sel.parentElement() === input) {
                    var rng = input.createTextRange();
                    rng.moveToBookmark(sel.getBookmark());
                    for (var len = 0;
                         rng.compareEndPoints("EndToStart", rng) > 0;
                         rng.moveEnd("character", -1)) {
                        len++;
                    }
                    rng.setEndPoint("StartToStart", input.createTextRange());
                    for (var pos = {start: 0, end: len};
                         rng.compareEndPoints("EndToStart", rng) > 0;
                         rng.moveEnd("character", -1)) {
                        pos.start++;
                        pos.end++;
                    }
                    return pos;
                }
            }
        }
        return {start: 0, end: 0};
    };

    utils.setCursorPosition = function (input, start, end) {
        if (arguments.length < 3) {
            end = start;
        }

        if ("selectionStart" in input) {
            setTimeout(function () {
                input.selectionStart = start;
                input.selectionEnd = end;
            }, 1);
        } else if (input.createTextRange) {
            var rng = input.createTextRange();
            rng.moveStart("character", start);
            rng.collapse();
            rng.moveEnd("character", end - start);
            rng.select();
        }
    };

    utils.getCookie = function (name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    utils.getFormData = function ($form) {
        var unindexed_array = $form.serializeArray();
        var indexed_array = {};

        $.map(unindexed_array, function (n, i) {
            indexed_array[n['name']] = n['value'];
        });

        return indexed_array;
    };

    utils.dataURItoBlob = function (dataURI) {
        // convert base64/URLEncoded data component to raw binary data held in a string
        var byteString;
        if (dataURI.split(',')[0].indexOf('base64') >= 0)
            byteString = atob(dataURI.split(',')[1]);
        else
            byteString = unescape(dataURI.split(',')[1]);
        // separate out the mime component
        var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
        // write the bytes of the string to a typed array
        var ia = new Uint8Array(byteString.length);
        for (var i = 0; i < byteString.length; i++) {
            ia[i] = byteString.charCodeAt(i);
        }
        return new Blob([ia], {type: mimeString});
    };

    utils.uploadFile = function (form, url, type) {
        form = $(form)[0];
        var formData = new FormData(form);
        return utils.uploadFileFormData(formData, (url || form.action), (type || form.method));
    };

    utils.dataToFormData = function (data) {
        data['csrfmiddlewaretoken'] = CSRF_TOKEN;
        var formData = new FormData();
        for (var key in data) {
            if (data.hasOwnProperty(key)) {
                formData.append(key, data[key]);
            }
        }

        return formData;

    };

    utils.uploadFileFormData = function (formData, url, type) {
        var errorHandler, beforeSendHandler, completeHandler;
        return $.ajax({
            url: url,  //Server script to process data
            type: type || 'POST',
            xhr: function () {  // Custom XMLHttpRequest
                var myXhr = $.ajaxSettings.xhr();
                if (myXhr.upload) { // Check if upload property exists
                    myXhr.upload.addEventListener('progress', progressHandlingFunction, false); // For handling the progress of the upload
                }
                return myXhr;
            },
            //Form data
            data: formData,
            //Options to tell jQuery not to process data or worry about content-type.
            cache: false,
            contentType: false,
            processData: false
        });

    };

    utils.submitFormById = function (formId) {
        var form = document.getElementById(formId);
        return utils.submitForm(form)
    };

    utils.submitForm = function (form) {

        var formData = {};
        $(form).serializeArray().reduce(function (obj, item) {
            formData[item.name] = item.value;
            return obj;
        }, {});

        return jQuery.post(form.action || '', formData);

    };

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    function progressHandlingFunction(e) {
        if (e.lengthComputable) {
            var percentVal = Math.round((e.loaded / e.total) * 100);
            var $progressContainer = $('.progress-container');
            if(percentVal === 100) {
                $progressContainer.hide();
            } else {
                $progressContainer.show();
            }

            percentVal += '%';

            $progressContainer.find('.progress-bar').css({'width': percentVal}).text(percentVal);
        }
    }

    utils.onAllImgLoaded = function ($container) {
        return new Promise(function (resolve) {
            var $imgs = $container.find('img');
            var img_count = 0;
            $imgs.each(function () {
                if (this.complete) {
                    img_count++;
                }
            });

            if (img_count === $imgs.length) {
                resolve();
                return;
            }

            $imgs.on('load', function () {
                img_count++;
                if (img_count === $imgs.length) {
                    resolve();
                }
            });
        });
    }

    /*$.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", utils.getCookie('csrftoken'));
            }
        }
    });*/

})(window.utils || (window.utils = {}));